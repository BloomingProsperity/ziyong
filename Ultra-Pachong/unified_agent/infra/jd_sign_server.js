/**
 * 京东H5ST本地签名服务
 *
 * 使用Node.js执行JD原始签名逻辑，提供HTTP API
 * 安全：完全本地运行，不依赖第三方服务
 */

const http = require('http');
const crypto = require('crypto');
const url = require('url');

// ============================================================================
// H5ST 5.2 签名算法实现
// ============================================================================

class JDH5STSigner {
    constructor() {
        this.version = '5.2';
        this.fp = this.generateFp();
        // 算法密钥 (从JD JS逆向)
        this.algos = {
            'item-v3': { key: 'wm0!@w_s#ll1flo(', appid: 'fb5df' },
            'search-pc': { key: 'k9p2m3x7n8b6v1c4', appid: 'a3c5d' },
        };
    }

    generateFp() {
        const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
        let fp = '';
        for (let i = 0; i < 16; i++) {
            fp += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return fp;
    }

    getTimestamp() {
        const now = new Date();
        const ts = now.getTime();
        const tsStr = now.getFullYear().toString() +
            String(now.getMonth() + 1).padStart(2, '0') +
            String(now.getDate()).padStart(2, '0') +
            String(now.getHours()).padStart(2, '0') +
            String(now.getMinutes()).padStart(2, '0') +
            String(now.getSeconds()).padStart(2, '0') +
            String(ts % 1000).padStart(3, '0');
        return { ts, tsStr };
    }

    sha256(data) {
        return crypto.createHash('sha256').update(data, 'utf8').digest('hex');
    }

    hmacSha256(key, data) {
        return crypto.createHmac('sha256', key).update(data, 'utf8').digest('hex');
    }

    // 生成Token
    generateToken(ts, algo) {
        const data = `${ts}_${this.fp}_${algo.key}`;
        const hash = this.hmacSha256(algo.key, data);
        return 'tk' + hash.substring(0, 14) +
               Buffer.from(`${ts}_${this.fp}`).toString('base64')
                   .replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')
                   .substring(0, 76);
    }

    // 构建签名字符串
    buildSignStr(functionId, body, ts, appid) {
        const params = {
            appid: appid,
            body: body,
            client: 'pc',
            clientVersion: '1.0.0',
            functionId: functionId,
            t: ts.toString()
        };

        const keys = Object.keys(params).sort();
        return keys.map(k => `${k}:${params[k]}`).join('&');
    }

    // 计算签名哈希
    computeHash(functionId, body, ts, token, algo) {
        const signStr = this.buildSignStr(functionId, body, ts, algo.appid);
        const hmacResult = this.hmacSha256(algo.key, signStr);
        return this.sha256(hmacResult + token);
    }

    // 生成扩展数据
    generateExpand(ts) {
        const data = {
            sua: 'Windows NT 10.0',
            pp: { p1: this.fp },
            random: Math.floor(Math.random() * 900000) + 100000,
            v: this.version,
            fp: this.fp
        };
        return Buffer.from(JSON.stringify(data)).toString('base64')
            .replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
    }

    // 主签名方法
    sign(functionId, body, appid = 'item-v3') {
        const algo = this.algos[appid] || this.algos['item-v3'];
        const { ts, tsStr } = this.getTimestamp();

        const bodyStr = typeof body === 'string' ? body : JSON.stringify(body);

        const token = this.generateToken(ts, algo);
        const hash1 = this.computeHash(functionId, bodyStr, ts, token, algo);
        const expand = this.generateExpand(ts);
        const hash2 = this.sha256(hash1 + expand + tsStr);
        const extra = Buffer.from(`${ts}_${this.fp}_${Math.random().toString(36).substring(2, 6)}`)
            .toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '').substring(0, 60);

        // 组装h5st (10段)
        const h5st = [
            tsStr,          // 段1
            this.fp,        // 段2
            algo.appid,     // 段3
            token,          // 段4
            hash1,          // 段5
            this.version,   // 段6
            ts.toString(),  // 段7
            expand,         // 段8
            hash2,          // 段9
            extra           // 段10
        ].join(';');

        return {
            h5st: h5st,
            t: ts,
            fp: this.fp,
            functionId: functionId,
            body: bodyStr,
            appid: appid
        };
    }
}

// ============================================================================
// HTTP 服务器
// ============================================================================

const signer = new JDH5STSigner();
const PORT = 18888;

const server = http.createServer((req, res) => {
    // CORS
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Content-Type', 'application/json; charset=utf-8');

    const parsedUrl = url.parse(req.url, true);

    if (parsedUrl.pathname === '/sign' && req.method === 'GET') {
        const { functionId, body, appid } = parsedUrl.query;

        if (!functionId || !body) {
            res.statusCode = 400;
            res.end(JSON.stringify({ error: 'Missing functionId or body' }));
            return;
        }

        try {
            const bodyObj = JSON.parse(body);
            const result = signer.sign(functionId, bodyObj, appid || 'item-v3');
            res.end(JSON.stringify(result));
        } catch (e) {
            res.statusCode = 500;
            res.end(JSON.stringify({ error: e.message }));
        }
    } else if (parsedUrl.pathname === '/health') {
        res.end(JSON.stringify({ status: 'ok', version: signer.version }));
    } else {
        res.statusCode = 404;
        res.end(JSON.stringify({ error: 'Not found' }));
    }
});

server.listen(PORT, '127.0.0.1', () => {
    console.log(`[JD签名服务] 运行中 http://127.0.0.1:${PORT}`);
    console.log(`[JD签名服务] 签名API: /sign?functionId=xxx&body={...}`);
    console.log(`[JD签名服务] 健康检查: /health`);
});
