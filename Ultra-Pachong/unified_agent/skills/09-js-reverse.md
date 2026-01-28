---
skill_id: "09-js-reverse"
name: "JS逆向深度模块"
version: "1.2.0"
status: "stable"                    # draft | beta | stable | deprecated
implementation_status: "none"       # none | partial | complete
difficulty: 5
category: "advanced"

description: "JavaScript代码分析、反混淆、算法还原与签名破解"

triggers:
  - condition: "signature.complexity >= 'high'"
  - pattern: "(逆向|反混淆|AST|webpack|签名算法|JS破解)"

dependencies:
  required:
    - skill: "03-signature"
      reason: "签名参数分析"
      min_version: "1.1.0"
  optional:
    - skill: "02-anti-detection"
      reason: "环境检测绕过"
      condition: "需要绕过反调试检测时"
      fallback: "使用真实浏览器环境"

external_dependencies:
  required: []
  optional:
    - name: "@babel/parser"
      version: ">=7.23.0"
      condition: "AST解析"
      type: "npm"
      install: "npm install @babel/parser @babel/traverse @babel/generator @babel/types"
    - name: "playwright"
      version: ">=1.40.0"
      condition: "RPC方案"
      type: "python_package"
      install: "pip install playwright"

inputs:
  - name: "js_code"
    type: "string"
    required: true
    description: "待分析的JavaScript代码"
  - name: "target_function"
    type: "string"
    required: false
    description: "目标函数名称(可选,用于精准定位)"
  - name: "analysis_depth"
    type: "int"
    required: false
    description: "分析深度 1-5, 默认3"

outputs:
  - name: "deobfuscated_code"
    type: "string"
    description: "反混淆后的代码"
  - name: "algorithm_impl"
    type: "string"
    description: "算法实现(Python或Node.js)"
  - name: "approach"
    type: "enum"
    description: "pure_algo | node_env | rpc | browser"

slo:
  - metric: "定位成功率"
    target: "≥ 90%"
    scope: "常见混淆(obfuscator.io/uglify-js/terser)"
    measurement: "成功定位目标函数数 / 尝试定位总数"
    degradation:
      - level: 1
        condition: "定位成功率 < 90%"
        action: "启用人工辅助定位模式"
      - level: 2
        condition: "定位成功率 < 70%"
        action: "切换到全局搜索+Hook方式"
  - metric: "反混淆成功率"
    target: "≥ 85%"
    scope: "变量重命名/字符串加密/控制流平坦化"
    measurement: "成功反混淆数 / 尝试反混淆总数"
    degradation:
      - level: 1
        condition: "反混淆成功率 < 85%"
        action: "降级到RPC方案(直接执行混淆代码)"
      - level: 2
        condition: "反混淆成功率 < 60%"
        action: "使用浏览器环境执行"
  - metric: "算法还原时间"
    target: "< 2小时"
    scope: "标准加密算法(MD5/SHA/HMAC/AES)"
    degradation:
      - level: 1
        condition: "还原时间 > 2小时"
        action: "切换补环境方案"

risks:
  - risk: "WASM模块分析"
    impact: "无法通过AST分析,逆向难度极高"
    mitigation: "使用RPC方案或wasm2wat工具分析"
  - risk: "反调试检测"
    impact: "DevTools打开时代码停止执行或返回假数据"
    mitigation: "使用反反调试插件或Frida注入"
  - risk: "代码自毁机制"
    impact: "检测到逆向行为时销毁关键代码"
    mitigation: "先完整保存原始代码,分析前关闭网络"

limitations:
  - "不支持极度混淆的WASM模块(需专业工具)"
  - "不处理需要特定硬件指令的加密(如SGX)"
  - "不支持需要服务端验证的动态代码生成"

tags:
  - "逆向工程"
  - "JavaScript"
  - "AST"
  - "反混淆"
  - "algorithm-reverse"
---

# 09 - JS逆向深度模块 (JavaScript Reverse Engineering)

## 模块目标

| 目标 | SLO | 适用范围 | 降级策略 |
|------|-----|----------|----------|
| 定位签名函数 | 成功率 ≥ 90% | 常见混淆 | 人工辅助 |
| 反混淆处理 | 成功率 ≥ 85% | 变量重命名/字符串加密/控制流平坦化 | RPC方案 |
| 算法还原 | Python/Node复现 | 标准加密算法 | 补环境执行 |
| 环境补全 | Node执行成功 | 常见浏览器API | Playwright RPC |
| 方案选择 | 自动最优 | 所有场景 | 人工干预 |

---

## 代码实现状态

> **当前状态**: 🚧 仅设计文档,无代码实现

| 功能模块 | 实现状态 | 代码位置 | 说明 |
|---------|---------|---------|------|
| AST反混淆引擎 | ❌ 未实现 | `N/A` | 需要Node.js环境 + Babel工具链 |
| WASM分析工具 | ❌ 未实现 | `N/A` | 需要wasm2wat/Ghidra集成 |
| 补环境框架 | ❌ 未实现 | `N/A` | 需要jsdom或类似库 |
| RPC桥接服务 | ⚠️ 部分实现 | `unified_agent/infra/sign_server.py` | 仅有基础RPC框架 |
| Hook脚本库 | ❌ 未实现 | `N/A` | 需要整理常用Hook模板 |

**替代方案**: 当前建议使用外部工具
- AST分析: 手工使用 `@babel/parser` + `@babel/traverse`
- WASM分析: 使用 Ghidra + WASM插件
- 补环境: 使用 jsdom 或 vm2
- RPC: 使用 Playwright 的 `page.evaluate()`

---

## 接口定义

### 输入

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| js_code | string | 是 | - | 待分析的JavaScript代码 |
| target_function | string | 否 | null | 目标函数名称(精准定位) |
| analysis_depth | int | 否 | 3 | 分析深度 1(浅)-5(深) |
| options | dict | 否 | {} | 额外配置选项 |

**options 可选字段**:
```python
{
    "deobfuscate": True,        # 是否反混淆
    "extract_constants": True,  # 是否提取常量
    "trace_calls": False,       # 是否追踪调用链
    "timeout": 300,             # 超时时间(秒)
}
```

### 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| status | enum | success / partial / failed |
| deobfuscated_code | string | 反混淆后的代码(可能为空) |
| algorithm_impl | string | Python或Node.js实现代码 |
| approach | enum | pure_algo / node_env / rpc / browser |
| confidence | float | 结果置信度 0.0-1.0 |
| warnings | list[str] | 警告信息 |
| errors | list[str] | 错误列表(可为空) |

### 错误码

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| E_JS_001 | 代码解析失败 | 检查代码完整性,可能需要补全上下文 |
| E_JS_002 | 目标函数未找到 | 尝试全局搜索或使用Hook方式定位 |
| E_JS_003 | 反混淆超时 | 降低analysis_depth或切换RPC方案 |
| E_JS_004 | WASM模块无法分析 | 使用wasm2wat或切换RPC方案 |
| E_JS_005 | 环境补全失败 | 检查缺失的API,手动补充或使用浏览器 |
| E_JS_006 | 算法识别失败 | 可能是自定义算法,建议RPC方案 |
| E_JS_007 | 反调试检测触发 | 使用反反调试插件或更换分析环境 |

---

## Skill 交互

### 上游 (谁调用我)

| Skill | 调用场景 | 传入数据 |
|-------|----------|----------|
| 03-signature | 签名复杂度为high/extreme时 | js_code(签名函数代码), target_function(如h5st) |
| 18-brain-controller | 用户明确要求逆向分析时 | js_code(目标JS文件), task_context |
| 16-tactics | 自动检测到复杂签名时 | js_code(捕获的加密代码) |

### 下游 (我调用谁)

| Skill | 调用场景 | 传出数据 |
|-------|----------|----------|
| 02-anti-detection | 检测到反调试时 | stealth_config(反检测配置) |
| 03-signature | 算法还原完成后 | algorithm_impl(签名实现代码) |
| 04-request | RPC方案时 | rpc_endpoint(远程执行地址) |

### 调用时序图

```
用户请求
   │
   ▼
03-signature (检测到high复杂度)
   │
   ├─→ 09-js-reverse.locate_function()
   │     └─→ XHR断点 / Hook / 搜索关键词
   │
   ├─→ 09-js-reverse.deobfuscate()
   │     └─→ AST解析 → 字符串解密 → 控制流还原
   │
   ├─→ 09-js-reverse.analyze_algorithm()
   │     └─→ 识别加密常量 → 推断算法类型
   │
   └─→ 09-js-reverse.choose_approach()
         │
         ├─ pure_algo → 03-signature.implement()
         ├─ node_env  → 补环境执行
         └─ rpc       → 04-request + browser
```

---

## 模块概述

JS逆向是突破高等级反爬的核心能力。本模块覆盖从定位到破解的完整流程。

```
┌─────────────────────────────────────────────────────────────────┐
│                      JS逆向完整流程                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐│
│  │ 定位   │──▶│ 分析   │──▶│ 反混淆 │──▶│ 还原   │──▶│ 复现   ││
│  │ Locate │   │Analyze │   │Deobfus │   │Restore │   │Replicate│
│  └────────┘   └────────┘   └────────┘   └────────┘   └────────┘│
│      │            │            │            │            │      │
│      ▼            ▼            ▼            ▼            ▼      │
│  找到签名     理解结构     去除混淆     算法还原     代码实现   │
│  生成位置     调用关系     可读代码     核心逻辑     Python/JS  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 第一步：定位签名生成位置

### 1.1 Chrome DevTools 断点技巧

#### XHR 断点
```
操作步骤:
1. F12 打开开发者工具
2. 切换到 "Sources" 面板
3. 右侧 "XHR/fetch Breakpoints"
4. 点击 "+" 添加断点
5. 输入 API URL 的关键词（如 "sign" 或 "h5st"）
6. 触发请求，代码会在发送前断住
7. 查看 Call Stack 找到签名生成位置
```

#### 事件监听断点
```
操作步骤:
1. Sources -> Event Listener Breakpoints
2. 展开 "XHR" 或 "Script"
3. 勾选相关事件
4. 触发操作，断点命中
```

#### 条件断点
```javascript
// 右键行号 -> Add conditional breakpoint
// 输入条件表达式

// 示例1: 参数包含特定值时断住
arguments[0] && arguments[0].includes('sign')

// 示例2: 特定函数被调用时
this.functionName === 'encrypt'

// 示例3: 变量值满足条件
data.length > 100
```

### 1.2 Hook 技巧

#### 全局 Hook 模板
```javascript
// === 在 Console 中执行以下代码 ===

// Hook JSON.stringify - 捕获所有 JSON 序列化
(function() {
    var stringify = JSON.stringify;
    JSON.stringify = function() {
        console.log('JSON.stringify 调用:');
        console.log('参数:', arguments);
        console.log('调用栈:', new Error().stack);
        return stringify.apply(this, arguments);
    };
})();

// Hook XMLHttpRequest - 捕获所有 XHR 请求
(function() {
    var open = XMLHttpRequest.prototype.open;
    var send = XMLHttpRequest.prototype.send;

    XMLHttpRequest.prototype.open = function(method, url) {
        this._url = url;
        this._method = method;
        console.log('XHR Open:', method, url);
        return open.apply(this, arguments);
    };

    XMLHttpRequest.prototype.send = function(data) {
        console.log('XHR Send:', this._method, this._url);
        console.log('Data:', data);
        console.log('Stack:', new Error().stack);
        return send.apply(this, arguments);
    };
})();

// Hook fetch - 捕获所有 fetch 请求
(function() {
    var originalFetch = window.fetch;
    window.fetch = function(url, options) {
        console.log('Fetch:', url);
        console.log('Options:', options);
        console.log('Stack:', new Error().stack);
        return originalFetch.apply(this, arguments);
    };
})();

// Hook 特定对象的属性
(function() {
    var obj = window.someObject;  // 替换为目标对象
    var originalProp = obj.targetProperty;

    Object.defineProperty(obj, 'targetProperty', {
        get: function() {
            console.log('读取 targetProperty');
            return originalProp;
        },
        set: function(val) {
            console.log('设置 targetProperty:', val);
            console.log('Stack:', new Error().stack);
            originalProp = val;
        }
    });
})();
```

#### 加密函数 Hook
```javascript
// Hook 常见加密库

// CryptoJS
if (window.CryptoJS) {
    var originalMD5 = CryptoJS.MD5;
    CryptoJS.MD5 = function() {
        console.log('CryptoJS.MD5:', arguments);
        return originalMD5.apply(this, arguments);
    };

    var originalHmacSHA256 = CryptoJS.HmacSHA256;
    CryptoJS.HmacSHA256 = function() {
        console.log('CryptoJS.HmacSHA256:', arguments);
        return originalHmacSHA256.apply(this, arguments);
    };
}

// 原生 crypto
if (window.crypto && window.crypto.subtle) {
    var originalDigest = crypto.subtle.digest;
    crypto.subtle.digest = function(algorithm, data) {
        console.log('crypto.subtle.digest:', algorithm);
        return originalDigest.apply(this, arguments);
    };
}
```

### 1.3 搜索技巧

#### 全局搜索关键词
```
在 DevTools Sources 面板按 Ctrl+Shift+F 全局搜索:

签名相关:
- sign
- signature
- token
- encrypt
- hash
- md5
- sha
- hmac
- secret

京东 h5st:
- h5st
- _ste
- paramsign
- algo

淘宝 mtop:
- mtop
- x-sign
- appKey

抖音:
- X-Bogus
- _signature
- msToken

小红书:
- X-s
- x-s-common
- shield
```

---

## 第二步：理解代码结构

### 2.1 Webpack 打包分析

#### Webpack 特征识别
```javascript
// 特征1: webpackJsonp 或 webpackChunk
window.webpackJsonp = window.webpackJsonp || [];
window.webpackChunk_xxx = window.webpackChunk_xxx || [];

// 特征2: 模块加载器结构
(function(modules) {
    function __webpack_require__(moduleId) {
        // ...
    }
})([
    /* 0 */ function(module, exports, __webpack_require__) { ... },
    /* 1 */ function(module, exports, __webpack_require__) { ... },
]);

// 特征3: 模块定义
__webpack_require__.d = function(exports, name, getter) { ... };
__webpack_require__.r = function(exports) { ... };
```

#### 提取 Webpack 模块
```javascript
// 方法1: 通过全局变量提取
// 在 Console 中执行

// 找到 webpack require 函数
var webpackRequire;
webpackJsonp.push([
    ['hack'],
    {
        'hack': function(module, exports, require) {
            webpackRequire = require;
        }
    },
    [['hack']]
]);

// 现在可以通过 webpackRequire(模块ID) 获取任意模块
var targetModule = webpackRequire(123);  // 替换为目标模块ID

// 方法2: 导出所有模块
var allModules = {};
for (var key in webpackRequire.c) {
    allModules[key] = webpackRequire.c[key].exports;
}
console.log(allModules);
```

#### Webpack 模块导出到全局
```javascript
// 将内部模块暴露到 window 以便调试
(function() {
    // 假设签名函数在模块 456 中
    var signModule = webpackRequire(456);

    // 导出到全局
    window.signModule = signModule;
    window.generateSign = signModule.generateSign || signModule.default;

    console.log('模块已导出到 window.signModule');
})();
```

### 2.2 调用链分析

#### 构建调用关系图
```javascript
// 使用递归追踪函数调用

function traceFunction(fn, name, depth = 0) {
    if (depth > 10) return;  // 防止无限递归

    return function(...args) {
        console.log('  '.repeat(depth) + `-> ${name}(`, args, ')');

        var result = fn.apply(this, args);

        console.log('  '.repeat(depth) + `<- ${name} =`, result);
        return result;
    };
}

// 应用到目标对象
var targetObj = window.someEncryptObject;
for (var key in targetObj) {
    if (typeof targetObj[key] === 'function') {
        targetObj[key] = traceFunction(targetObj[key], key);
    }
}
```

---

## 第三步：反混淆技术

### 3.1 常见混淆类型

| 混淆类型 | 特征 | 还原难度 |
|---------|------|---------|
| 变量重命名 | a, b, _0x1234 | ⭐ 低 |
| 字符串加密 | _0x1234('0x1') | ⭐⭐ 中 |
| 控制流平坦化 | switch-case 嵌套 | ⭐⭐⭐ 高 |
| 死代码注入 | 无用的 if-else | ⭐⭐ 中 |
| 对象键名混淆 | obj['a'+'b'] | ⭐⭐ 中 |
| eval/Function | eval(decryptedCode) | ⭐⭐⭐ 高 |
| WASM | WebAssembly 模块 | ⭐⭐⭐⭐ 极高 |

### 3.2 AST 反混淆

#### 环境准备
```bash
# 安装 Node.js 依赖
npm install @babel/parser @babel/traverse @babel/generator @babel/types
```

#### 基础 AST 操作
```javascript
// deobfuscate.js - 反混淆脚本模板

const parser = require('@babel/parser');
const traverse = require('@babel/traverse').default;
const generator = require('@babel/generator').default;
const t = require('@babel/types');
const fs = require('fs');

// 读取混淆代码
const code = fs.readFileSync('obfuscated.js', 'utf-8');

// 解析为 AST
const ast = parser.parse(code);

// ========== 反混淆规则 ==========

// 规则1: 计算常量表达式
// 将 1 + 2 直接计算为 3
traverse(ast, {
    BinaryExpression(path) {
        const { left, right, operator } = path.node;
        if (t.isNumericLiteral(left) && t.isNumericLiteral(right)) {
            let result;
            switch (operator) {
                case '+': result = left.value + right.value; break;
                case '-': result = left.value - right.value; break;
                case '*': result = left.value * right.value; break;
                case '/': result = left.value / right.value; break;
                default: return;
            }
            path.replaceWith(t.numericLiteral(result));
        }
    }
});

// 规则2: 字符串拼接还原
// 将 'hel' + 'lo' 还原为 'hello'
traverse(ast, {
    BinaryExpression(path) {
        const { left, right, operator } = path.node;
        if (operator === '+' &&
            t.isStringLiteral(left) &&
            t.isStringLiteral(right)) {
            path.replaceWith(t.stringLiteral(left.value + right.value));
        }
    }
});

// 规则3: 删除无用代码
// 删除 if (false) { ... }
traverse(ast, {
    IfStatement(path) {
        const test = path.node.test;
        if (t.isBooleanLiteral(test)) {
            if (test.value === false) {
                path.remove();
            } else if (test.value === true && path.node.consequent) {
                path.replaceWithMultiple(
                    path.node.consequent.body || [path.node.consequent]
                );
            }
        }
    }
});

// 生成还原后的代码
const output = generator(ast, {
    comments: false,
    compact: false
});

fs.writeFileSync('deobfuscated.js', output.code);
console.log('反混淆完成!');
```

### 3.3 字符串解密

#### 字符串数组解密
```javascript
// 混淆代码通常有这样的结构:
var _0x1234 = ['aGVsbG8=', 'd29ybGQ=', ...];  // Base64编码的字符串

function _0x5678(index) {
    return atob(_0x1234[index]);  // 解密函数
}

// 使用时: _0x5678(0) 返回 'hello'

// ========== 解密脚本 ==========

// 方法1: 执行解密函数，直接替换
traverse(ast, {
    CallExpression(path) {
        const { callee, arguments: args } = path.node;

        // 匹配 _0x5678(0) 这样的调用
        if (t.isIdentifier(callee) &&
            callee.name === '_0x5678' &&  // 解密函数名
            args.length === 1 &&
            t.isNumericLiteral(args[0])) {

            // 获取真实字符串 (需要在 Node 中执行解密函数)
            const realString = decryptFunction(args[0].value);
            path.replaceWith(t.stringLiteral(realString));
        }
    }
});

// 方法2: 动态执行获取解密结果
const vm = require('vm');
const context = { result: null };

// 提取字符串数组和解密函数
const decryptCode = `
    var _0x1234 = ['aGVsbG8=', 'd29ybGQ='];
    function _0x5678(i) { return atob(_0x1234[i]); }
`;

// 在沙箱中执行
vm.runInNewContext(decryptCode + '; result = _0x5678(0);', context);
console.log(context.result);  // 'hello'
```

### 3.4 控制流平坦化还原

#### 识别特征
```javascript
// 平坦化后的代码特征
function obfuscatedFunc() {
    var state = '1';
    while (true) {
        switch (state) {
            case '1':
                // 代码块1
                state = '3';
                break;
            case '2':
                // 代码块2
                return result;
            case '3':
                // 代码块3
                state = '2';
                break;
        }
    }
}
```

#### 还原算法
```javascript
// 控制流平坦化还原

traverse(ast, {
    WhileStatement(path) {
        const body = path.node.body;
        if (!t.isBlockStatement(body)) return;

        const switchStmt = body.body[0];
        if (!t.isSwitchStatement(switchStmt)) return;

        // 收集所有 case
        const cases = {};
        switchStmt.cases.forEach(caseNode => {
            const key = caseNode.test.value;
            cases[key] = caseNode.consequent;
        });

        // 按执行顺序重建代码
        const orderedCode = [];
        let currentState = findInitialState(path);  // 找到初始状态

        while (currentState && cases[currentState]) {
            const block = cases[currentState];
            orderedCode.push(...block.filter(s => !isStateAssignment(s)));
            currentState = getNextState(block);  // 获取下一个状态
        }

        // 替换整个 while 循环
        path.replaceWithMultiple(orderedCode);
    }
});
```

### 3.5 反混淆工具推荐

| 工具 | 类型 | 适用场景 | 地址 |
|------|------|---------|------|
| AST Explorer | 在线 | AST 结构查看 | astexplorer.net |
| de4js | 在线 | 通用反混淆 | lelinhtinh.github.io/de4js |
| JStillery | 在线 | 动态分析 | mindedsecurity.github.io/jstillery |
| synchrony | 命令行 | 自动反混淆 | github.com/nickcano/synchrony |
| js-beautify | npm | 格式化 | github.com/beautify-web/js-beautify |
| babel | npm | AST 操作 | babeljs.io |

---

## 第四步：算法还原

### 4.1 常见加密算法识别

#### MD5 特征
```javascript
// MD5 常量识别
0x67452301  // A
0xefcdab89  // B
0x98badcfe  // C
0x10325476  // D

// 或者十进制
1732584193, 4023233417, 2562383102, 271733878

// 循环左移操作
(x << n) | (x >>> (32 - n))

// S-box 表
[7, 12, 17, 22, ...]
```

#### SHA256 特征
```javascript
// 初始哈希值
0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19

// K 常量表 (前几个)
0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5...
```

#### HMAC 特征
```javascript
// 两次哈希
// inner = hash(key XOR ipad, message)
// outer = hash(key XOR opad, inner)

// ipad = 0x36 重复
// opad = 0x5c 重复
```

#### AES 特征
```javascript
// S-box 表
[0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, ...]

// 轮常量
[0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36]

// 16 字节块操作
SubBytes, ShiftRows, MixColumns, AddRoundKey
```

### 4.2 京东 H5ST 算法分析

#### H5ST 结构
```
h5st = {timestamp};{fingerprint};{version};{hash}

示例: 20240127120000000;1234567890123;4.7;a1b2c3d4e5f6...
```

#### 关键函数定位
```javascript
// 搜索关键词
- "h5st"
- "paramsign"
- "_ste"
- "algo"
- "4.7" (版本号)

// 典型函数签名
function generateH5st(params) {
    var timestamp = getTimestamp();
    var fingerprint = getFingerprint();
    var version = '4.7';
    var hash = hmacSHA256(sortParams(params), getKey());
    return [timestamp, fingerprint, version, hash].join(';');
}
```

#### Python 复现模板
```python
import hashlib
import hmac
import time
import json

class JDH5ST:
    """京东 H5ST 签名生成器"""

    def __init__(self):
        self.version = "4.7"
        self.fingerprint = self._generate_fingerprint()

    def _generate_fingerprint(self):
        """生成设备指纹 (13位数字)"""
        import random
        return str(random.randint(1000000000000, 9999999999999))

    def _get_timestamp(self):
        """获取时间戳 (17位)"""
        return time.strftime("%Y%m%d%H%M%S") + "000"

    def _sort_params(self, params):
        """参数排序"""
        return "&".join(f"{k}={v}" for k, v in sorted(params.items()))

    def _get_key(self, timestamp):
        """
        获取签名密钥
        注意: 实际密钥生成更复杂，需要逆向分析
        """
        # 这里只是示例，实际需要根据逆向结果实现
        return f"key_{timestamp}"

    def generate(self, params):
        """生成 h5st 签名"""
        timestamp = self._get_timestamp()
        sorted_params = self._sort_params(params)
        key = self._get_key(timestamp)

        # HMAC-SHA256
        hash_value = hmac.new(
            key.encode(),
            sorted_params.encode(),
            hashlib.sha256
        ).hexdigest()

        return f"{timestamp};{self.fingerprint};{self.version};{hash_value}"


# 使用
h5st = JDH5ST()
params = {
    "functionId": "xxx",
    "body": "{}",
    "appid": "pc-item-soa"
}
sign = h5st.generate(params)
print(sign)
```

### 4.3 抖音 X-Bogus 算法分析

#### 特征识别
```javascript
// X-Bogus 通常由 WASM 生成
// 搜索关键词:
- "X-Bogus"
- "webmssdk"
- "bdms.js"
- "wasm"

// 典型调用
window.byted_acrawler.sign({
    url: requestUrl,
    ...
})
```

#### WASM 分析方法
```javascript
// 1. Hook WebAssembly 实例化
(function() {
    var originalInstantiate = WebAssembly.instantiate;
    WebAssembly.instantiate = function(bufferSource, importObject) {
        console.log('WASM instantiate called');
        console.log('Import object:', importObject);

        return originalInstantiate.apply(this, arguments).then(result => {
            console.log('WASM exports:', Object.keys(result.instance.exports));

            // Hook 导出函数
            for (var key in result.instance.exports) {
                if (typeof result.instance.exports[key] === 'function') {
                    var original = result.instance.exports[key];
                    result.instance.exports[key] = function(...args) {
                        console.log(`WASM ${key} called:`, args);
                        var ret = original.apply(this, args);
                        console.log(`WASM ${key} returned:`, ret);
                        return ret;
                    };
                }
            }

            return result;
        });
    };
})();
```

---

## 第五步：代码复现

### 5.1 补环境技术

#### Node.js 环境补全
```javascript
// env.js - 浏览器环境模拟

// 基础对象
global.window = global;
global.self = global;

// Navigator
global.navigator = {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    platform: 'Win32',
    language: 'zh-CN',
    languages: ['zh-CN', 'zh', 'en'],
    cookieEnabled: true,
    onLine: true,
    appName: 'Netscape',
    appVersion: '5.0',
    vendor: 'Google Inc.',
    plugins: { length: 3 },
};

// Document
global.document = {
    cookie: '',
    referrer: 'https://www.example.com/',
    title: 'Example',
    createElement: function(tag) {
        return {
            tagName: tag.toUpperCase(),
            style: {},
            setAttribute: function() {},
            getAttribute: function() {},
            appendChild: function() {},
        };
    },
    getElementById: function() { return null; },
    querySelector: function() { return null; },
    querySelectorAll: function() { return []; },
    body: { appendChild: function() {} },
    head: { appendChild: function() {} },
};

// Location
global.location = {
    href: 'https://www.example.com/',
    origin: 'https://www.example.com',
    protocol: 'https:',
    host: 'www.example.com',
    hostname: 'www.example.com',
    port: '',
    pathname: '/',
    search: '',
    hash: '',
};

// Screen
global.screen = {
    width: 1920,
    height: 1080,
    availWidth: 1920,
    availHeight: 1040,
    colorDepth: 24,
    pixelDepth: 24,
};

// LocalStorage
global.localStorage = {
    _data: {},
    getItem: function(key) { return this._data[key] || null; },
    setItem: function(key, value) { this._data[key] = String(value); },
    removeItem: function(key) { delete this._data[key]; },
    clear: function() { this._data = {}; },
};

global.sessionStorage = { ...global.localStorage, _data: {} };

// Canvas (简单模拟)
global.HTMLCanvasElement = function() {};
global.HTMLCanvasElement.prototype.getContext = function() {
    return {
        fillRect: function() {},
        fillText: function() {},
        measureText: function() { return { width: 10 }; },
        getImageData: function() { return { data: new Uint8Array(100) }; },
    };
};

// 其他常用对象
global.atob = require('atob');
global.btoa = require('btoa');
global.XMLHttpRequest = require('xmlhttprequest').XMLHttpRequest;
global.fetch = require('node-fetch');

// 时间相关
global.performance = {
    now: function() { return Date.now(); },
    timing: { navigationStart: Date.now() },
};

// 事件
global.Event = function(type) { this.type = type; };
global.CustomEvent = global.Event;

console.log('环境补全完成');
```

#### 使用补环境执行签名
```javascript
// run_sign.js

// 1. 加载环境
require('./env.js');

// 2. 加载目标 JS (反混淆后的)
const signCode = require('fs').readFileSync('./deobfuscated_sign.js', 'utf-8');
eval(signCode);

// 3. 调用签名函数
const params = {
    functionId: 'test',
    body: '{}',
};

const sign = window.generateSign(params);  // 假设签名函数已挂载到 window
console.log('Sign:', sign);

// 4. 导出为 HTTP 服务
const http = require('http');
http.createServer((req, res) => {
    // 解析请求参数
    const url = new URL(req.url, 'http://localhost');
    const params = Object.fromEntries(url.searchParams);

    // 生成签名
    const sign = window.generateSign(params);

    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ sign }));
}).listen(3000);

console.log('Sign server running on http://localhost:3000');
```

### 5.2 RPC 远程调用

#### 浏览器端注入
```javascript
// inject.js - 注入到浏览器中

(function() {
    // WebSocket 连接到本地服务
    var ws = new WebSocket('ws://127.0.0.1:9999');

    ws.onopen = function() {
        console.log('RPC 连接成功');
    };

    ws.onmessage = function(event) {
        var request = JSON.parse(event.data);

        try {
            // 执行签名函数
            var result;
            switch (request.method) {
                case 'generateSign':
                    result = window.generateSign(request.params);
                    break;
                case 'getH5st':
                    result = window._ste.sign(request.params);
                    break;
                default:
                    throw new Error('Unknown method: ' + request.method);
            }

            ws.send(JSON.stringify({
                id: request.id,
                result: result
            }));
        } catch (e) {
            ws.send(JSON.stringify({
                id: request.id,
                error: e.message
            }));
        }
    };

    ws.onclose = function() {
        console.log('RPC 连接断开，5秒后重连...');
        setTimeout(arguments.callee.bind(this), 5000);
    };
})();
```

#### Python RPC 客户端
```python
# rpc_client.py

import asyncio
import websockets
import json
import uuid

class JSBridge:
    """JS RPC 客户端"""

    def __init__(self, uri='ws://127.0.0.1:9999'):
        self.uri = uri
        self.ws = None
        self.pending = {}

    async def connect(self):
        self.ws = await websockets.connect(self.uri)
        asyncio.create_task(self._receive_loop())

    async def _receive_loop(self):
        async for message in self.ws:
            data = json.loads(message)
            request_id = data.get('id')
            if request_id in self.pending:
                self.pending[request_id].set_result(data)

    async def call(self, method, params):
        request_id = str(uuid.uuid4())
        future = asyncio.get_event_loop().create_future()
        self.pending[request_id] = future

        await self.ws.send(json.dumps({
            'id': request_id,
            'method': method,
            'params': params
        }))

        result = await future
        del self.pending[request_id]

        if 'error' in result:
            raise Exception(result['error'])
        return result['result']


# 使用示例
async def main():
    bridge = JSBridge()
    await bridge.connect()

    # 调用浏览器中的签名函数
    sign = await bridge.call('generateSign', {
        'url': 'https://api.example.com/data',
        'params': {'id': '123'}
    })

    print(f'Sign: {sign}')


asyncio.run(main())
```

---

## 第六步：调试技巧汇总

### 6.1 控制台高级用法

```javascript
// 格式化输出
console.log('%c 重要信息 ', 'background: red; color: white; font-size: 16px');
console.table([{a:1, b:2}, {a:3, b:4}]);
console.group('分组');
console.log('内容1');
console.log('内容2');
console.groupEnd();

// 性能测量
console.time('签名生成');
var sign = generateSign(params);
console.timeEnd('签名生成');

// 条件断点输出
console.count('函数调用次数');

// 追踪调用栈
console.trace('调用追踪');

// 断言
console.assert(sign.length === 128, '签名长度应为128');
```

### 6.2 内存断点

```javascript
// 在 Sources 面板中设置:
// 1. 选择变量
// 2. 右键 -> "Store as global variable"
// 3. 得到 temp1, temp2... 全局变量

// 监视表达式
// Watch -> Add Expression
// 输入: temp1.sign

// 内存快照对比
// Memory -> Take heap snapshot
// 执行操作前后各拍一次，对比差异
```

### 6.3 网络重放

```javascript
// 复制请求为 fetch
// Network -> 右键请求 -> Copy -> Copy as fetch

// 示例
fetch("https://api.example.com/data", {
  "headers": {
    "accept": "application/json",
    "content-type": "application/json",
  },
  "body": "{\"key\":\"value\"}",
  "method": "POST",
});
```

---

## 使用示例

### 示例1: 基础反混淆 - B站WBI签名

**场景**: 分析B站WBI签名算法(中等难度)

```python
from unified_agent import Brain

brain = Brain()

# 1. 获取混淆代码(假设已从Chrome DevTools提取)
js_code = """
var _0x1234 = ['wbi', 'sign', 'md5'];
function _0x5678(a, b) {
    return _0x1234[a] + b;
}
// ... 更多混淆代码
"""

# 2. 调用逆向分析
result = brain.js_reverse.deobfuscate(
    js_code=js_code,
    target_function="getWbiKeys",
    analysis_depth=3
)

# 3. 查看结果
if result.status == "success":
    print("反混淆后的代码:")
    print(result.deobfuscated_code)

    print(f"\n推荐方案: {result.approach}")
    print(f"置信度: {result.confidence}")

    if result.algorithm_impl:
        print("\nPython实现:")
        print(result.algorithm_impl)
else:
    print(f"失败: {result.errors}")
```

**预期输出**:
```python
# 反混淆后的代码:
def getWbiKeys(img_key, sub_key):
    mixin_key = img_key + sub_key
    mixin_key = ''.join(mixin_key[i] for i in MIXIN_KEY_ENC_TAB)[:32]
    return mixin_key

# 推荐方案: pure_algo
# 置信度: 0.95

# Python实现:
import hashlib
from urllib.parse import urlencode

MIXIN_KEY_ENC_TAB = [46, 47, 18, 2, 53, ...]

def sign_wbi(params: dict, img_key: str, sub_key: str) -> dict:
    mixin_key = get_mixin_key(img_key + sub_key)
    params['wts'] = int(time.time())
    query = urlencode(sorted(params.items()))
    w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()
    params['w_rid'] = w_rid
    return params
```

---

### 示例2: WASM分析 - 抖音X-Bogus

**场景**: 分析抖音X-Bogus(极高难度,WASM实现)

```python
# 1. 尝试分析WASM模块
result = brain.js_reverse.analyze_wasm(
    js_code=obfuscated_js_with_wasm,
    target_function="generate_x_bogus"
)

# 2. 检测到WASM,自动降级到RPC方案
if result.approach == "rpc":
    print("检测到WASM模块,建议使用RPC方案")

    # 3. 启动浏览器RPC服务
    rpc_server = brain.js_reverse.start_rpc_service(
        js_code=original_js,
        port=9999
    )

    # 4. 通过RPC调用签名函数
    x_bogus = rpc_server.call(
        method="generate_x_bogus",
        params={"url": "https://www.douyin.com/aweme/v1/web/aweme/detail/"}
    )

    print(f"X-Bogus: {x_bogus}")
```

**预期输出**:
```
检测到WASM模块,建议使用RPC方案
[RPC] 启动浏览器实例: Chromium
[RPC] 注入JS代码: 完成
[RPC] WebSocket服务启动: ws://127.0.0.1:9999
[RPC] 等待调用...

X-Bogus: DFSzswVOxGsANxYftx3G3C9WKa9e
```

---

### 示例3: 补环境执行 - 京东H5ST

**场景**: 京东H5ST签名(极高难度,需要补环境)

```python
# 1. 提取并反混淆签名函数
result = brain.js_reverse.deobfuscate(
    js_code=h5st_js_code,
    target_function="_ste.sign",
    analysis_depth=4
)

# 2. 检测到需要浏览器环境
if result.warnings:
    print("警告:", result.warnings)
    # ['需要 navigator', '需要 localStorage', '需要 Canvas']

# 3. 使用补环境方案
env_result = brain.js_reverse.execute_with_env(
    js_code=result.deobfuscated_code,
    env_config={
        "navigator": True,
        "localStorage": True,
        "canvas": True,
    }
)

# 4. 调用签名函数
h5st = env_result.call_function(
    function_name="_ste.sign",
    args={
        "functionId": "productDetail",
        "body": "{}",
        "appid": "item-v3"
    }
)

print(f"H5ST: {h5st}")
```

**预期输出**:
```
警告: ['需要 navigator', '需要 localStorage', '需要 Canvas']
[ENV] 创建Node.js虚拟环境
[ENV] 注入 navigator 对象
[ENV] 注入 localStorage 对象
[ENV] 注入 Canvas Mock
[ENV] 执行代码: 成功
[ENV] 调用函数: _ste.sign

H5ST: 20240128120000000;1234567890123;4.7;a1b2c3d4e5f6...
```

---

## 配置选项

### 全局配置

```python
# config.py 或环境变量

JS_REVERSE_CONFIG = {
    # AST分析配置
    "ast": {
        "max_iterations": 10,        # 最大迭代次数
        "timeout": 300,              # 超时时间(秒)
        "beautify": True,            # 是否美化输出
    },

    # 补环境配置
    "env": {
        "node_path": "node",         # Node.js路径
        "temp_dir": "./temp/js",     # 临时文件目录
        "cleanup": True,             # 执行后清理
    },

    # RPC配置
    "rpc": {
        "browser": "chromium",       # chromium | firefox | webkit
        "headless": True,            # 是否无头模式
        "port": 9999,                # WebSocket端口
        "timeout": 30,               # 调用超时(秒)
    },

    # 降级策略
    "fallback": {
        "auto_switch": True,         # 自动切换方案
        "max_retries": 3,            # 最大重试次数
        "escalate_threshold": 0.7,   # 置信度阈值
    }
}
```

### 运行时配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| deobfuscate | bool | True | 是否反混淆 |
| extract_constants | bool | True | 是否提取常量 |
| trace_calls | bool | False | 是否追踪调用链(性能开销大) |
| save_intermediate | bool | False | 是否保存中间结果 |
| use_cache | bool | True | 是否使用分析缓存 |
| log_level | str | "INFO" | 日志级别 DEBUG/INFO/WARN/ERROR |

---

## 诊断日志

### 标准日志格式

```
[JS_REVERSE] <阶段> <操作>: <详情>
```

### 正常流程日志

```
# 定位阶段
[JS_REVERSE] LOCATE 开始定位目标函数: generate_sign
[JS_REVERSE] LOCATE 搜索关键词: sign, signature, encrypt
[JS_REVERSE] LOCATE 命中文件: bundle.min.js:1234
[JS_REVERSE] LOCATE XHR断点触发: /api/getData
[JS_REVERSE] LOCATE Hook捕获调用: window.crypto.subtle.digest
[JS_REVERSE] LOCATE 定位完成: 函数位于行1234-1567

# 分析阶段
[JS_REVERSE] ANALYZE 检测混淆类型: obfuscator.io (控制流平坦化)
[JS_REVERSE] ANALYZE 检测到Webpack: chunk_id=vendor, module_id=4829
[JS_REVERSE] ANALYZE 提取模块: webpackRequire(4829)
[JS_REVERSE] ANALYZE 调用链分析: generateSign → hmacSHA256 → CryptoJS

# 反混淆阶段
[JS_REVERSE] DEOBFUS 解析AST: 成功 (14892个节点)
[JS_REVERSE] DEOBFUS 字符串解密: 解密89个字符串
[JS_REVERSE] DEOBFUS 控制流还原: 还原12个代码块
[JS_REVERSE] DEOBFUS 常量计算: 折叠45个表达式
[JS_REVERSE] DEOBFUS 变量重命名: _0x1234 → timestamp
[JS_REVERSE] DEOBFUS 反混淆完成: 耗时3.2s

# 算法识别阶段
[JS_REVERSE] ALGO 识别算法: HMAC-SHA256 (置信度0.95)
[JS_REVERSE] ALGO 特征常量匹配: 0x428a2f98 (SHA256_K表)
[JS_REVERSE] ALGO 输入输出分析: {params} → hex(64字符)
[JS_REVERSE] ALGO 依赖库检测: CryptoJS v4.1.1

# 方案选择阶段
[JS_REVERSE] APPROACH 评估复杂度: medium
[JS_REVERSE] APPROACH 方案打分: pure_algo=0.8, node_env=0.6, rpc=0.9
[JS_REVERSE] APPROACH 选择方案: pure_algo (最高分)
[JS_REVERSE] APPROACH 生成Python实现: 完成

# 验证阶段
[JS_REVERSE] VERIFY 测试输入: {id: 123, t: 1706432100}
[JS_REVERSE] VERIFY 预期输出: a1b2c3d4e5f6...
[JS_REVERSE] VERIFY 实际输出: a1b2c3d4e5f6...
[JS_REVERSE] VERIFY 验证成功: 输出一致
```

### 错误日志格式

```
# 定位失败
[JS_REVERSE] LOCATE ERROR: 目标函数未找到
[JS_REVERSE] LOCATE 尝试次数: 3
[JS_REVERSE] LOCATE 搜索范围: 12个JS文件, 共3.2MB
[JS_REVERSE] LOCATE 建议: 尝试Hook方式或人工定位

# 反混淆失败
[JS_REVERSE] DEOBFUS ERROR: AST解析失败: Unexpected token (1:45)
[JS_REVERSE] DEOBFUS 可能原因: 代码不完整或语法错误
[JS_REVERSE] DEOBFUS 建议: 检查代码完整性,补全上下文

# 算法识别失败
[JS_REVERSE] ALGO WARN: 无法识别算法类型
[JS_REVERSE] ALGO 分析结果: 可能是自定义算法
[JS_REVERSE] ALGO 建议: 使用RPC方案或补环境执行

# 环境补全失败
[JS_REVERSE] ENV ERROR: 缺失API: window.crypto.subtle
[JS_REVERSE] ENV 已补全: navigator, localStorage, document
[JS_REVERSE] ENV 未补全: crypto.subtle (Web Crypto API)
[JS_REVERSE] ENV 建议: 使用真实浏览器环境

# WASM分析失败
[JS_REVERSE] WASM ERROR: WASM模块过于复杂
[JS_REVERSE] WASM 大小: 512KB
[JS_REVERSE] WASM 混淆: 控制流平坦化 + 字符串加密
[JS_REVERSE] WASM 建议: 使用RPC方案绕过分析

# 验证失败
[JS_REVERSE] VERIFY ERROR: 输出不一致
[JS_REVERSE] VERIFY 预期: a1b2c3d4e5f6789012345678abcdefgh
[JS_REVERSE] VERIFY 实际: x9y8z7w6v5u4t3s2r1q0p9o8n7m6l5k4
[JS_REVERSE] VERIFY 差异: 完全不同(可能算法理解错误)
[JS_REVERSE] VERIFY 建议: 重新分析算法或使用RPC方案
```

### AI 自诊断检查点

```python
AI_DIAGNOSTIC_CHECKLIST = [
    # 定位阶段检查
    {
        "checkpoint": "LOCATE_FUNCTION",
        "checks": [
            "目标函数名是否正确?",
            "是否在正确的JS文件中搜索?",
            "是否被Webpack打包需要提取模块?",
            "是否需要触发特定操作才会加载?",
        ],
        "auto_fix": [
            "尝试全局搜索所有JS文件",
            "使用XHR断点+调用栈定位",
            "Hook常见加密函数",
        ]
    },

    # 反混淆阶段检查
    {
        "checkpoint": "DEOBFUSCATE",
        "checks": [
            "混淆类型是否正确识别?",
            "字符串数组是否完整提取?",
            "控制流还原是否正确?",
            "是否有反调试代码干扰?",
        ],
        "auto_fix": [
            "增加analysis_depth",
            "手动提取字符串数组",
            "移除反调试代码",
        ]
    },

    # 算法识别阶段检查
    {
        "checkpoint": "IDENTIFY_ALGORITHM",
        "checks": [
            "特征常量是否匹配标准算法?",
            "输入输出格式是否符合预期?",
            "是否有额外的自定义处理?",
        ],
        "auto_fix": [
            "对比标准库实现",
            "使用已知输入测试输出",
            "检查是否有SALT/IV参数",
        ]
    },

    # 执行验证阶段检查
    {
        "checkpoint": "VERIFY_OUTPUT",
        "checks": [
            "测试输入是否与实际一致?",
            "时间戳格式是否正确?",
            "参数顺序是否影响结果?",
            "是否有隐藏的全局变量影响?",
        ],
        "auto_fix": [
            "使用实际请求参数测试",
            "检查时间戳精度(秒/毫秒)",
            "尝试不同参数排序",
            "Hook所有全局变量",
        ]
    },
]
```

---

## 常见问题

### Q: 代码太复杂看不懂怎么办？
A:
1. 先格式化代码 (js-beautify)
2. 从入口函数开始追踪
3. 只关注参数和返回值
4. 用 Hook 记录关键变量

### Q: 反混淆后代码还是很乱？
A:
1. 多次迭代反混淆
2. 手动重命名变量
3. 添加注释标记关键逻辑
4. 画调用流程图

### Q: 怎么判断算法是不是标准算法？
A:
1. 搜索特征常量
2. 对比算法流程
3. 用已知输入测试输出
4. 对比标准库结果

---

## 诊断日志

```
# 定位阶段
[JS_LOCATE] 搜索关键词: {keyword}
[JS_LOCATE] 命中文件: {file_path}:{line_number}
[JS_LOCATE] XHR断点触发: {url}
[JS_LOCATE] Hook捕获: {function_name}({arguments})

# 分析阶段
[JS_ANALYZE] 检测到Webpack打包: {chunk_name}
[JS_ANALYZE] 模块ID: {module_id}, 导出: {exports}
[JS_ANALYZE] 调用链: {call_chain}

# 反混淆阶段
[JS_DEOBFUS] 混淆类型: {obfuscation_type}
[JS_DEOBFUS] 解密字符串: {count}个
[JS_DEOBFUS] 控制流还原: {blocks}个代码块

# 算法还原阶段
[JS_ALGO] 识别算法: {algorithm_name}
[JS_ALGO] 特征常量匹配: {constants}
[JS_ALGO] 输入: {input} -> 输出: {output}

# 复现阶段
[JS_IMPL] 方案选择: {approach} (纯算/补环境/RPC)
[JS_IMPL] 环境补全: {missing_objects}
[JS_IMPL] 签名验证: {expected} vs {actual}

# 错误情况
[JS_LOCATE] ERROR: 无法定位签名函数, 尝试: {attempts}
[JS_DEOBFUS] ERROR: 反混淆失败: {error}
[JS_IMPL] ERROR: 签名不匹配, 差异: {diff}
```

---

## 策略协调

当 JS 逆向遇到困难时，参考 [16-战术决策模块](16-tactics.md) 选择替代方案：
- **纯算法复杂** → 降级到补环境方案
- **补环境检测多** → 降级到 RPC 远程调用
- **逆向耗时过长** → 评估是否切换到浏览器自动化

### Q: 如何快速判断应该用哪种方案?

A: 根据以下决策树:
```
1. 能看懂代码逻辑?
   └─ 是 → pure_algo (纯算法复现)
   └─ 否 → 继续

2. 反混淆后能看懂?
   └─ 是 → pure_algo
   └─ 否 → 继续

3. 补环境能跑通?
   └─ 是 → node_env (补环境执行)
   └─ 否 → 继续

4. 所有情况 → rpc (浏览器RPC)
```

### Q: 反混淆后代码还是看不懂怎么办?

A:
1. 不要试图理解每一行代码
2. 只关注输入和输出
3. 使用Hook记录中间值
4. 画数据流图
5. 如果实在复杂,直接用RPC方案

### Q: WASM模块如何分析?

A:
1. **简单WASM**: 使用 wasm2wat 转文本格式查看
2. **复杂WASM**: 不要浪费时间,直接RPC方案
3. **工具推荐**: Ghidra + WASM插件 (仅学习用)
4. **实战建议**: WASM通常是为了防止逆向,成本太高

### Q: 如何验证算法还原是否正确?

A:
```python
# 1. 使用实际请求参数
test_params = {
    "functionId": "productDetail",
    "body": "{}",
    "t": 1706432100000,
}

# 2. 分别用原始JS和还原算法生成
original_sign = call_original_js(test_params)
restored_sign = my_algorithm(test_params)

# 3. 对比结果
if original_sign == restored_sign:
    print("验证成功!")
else:
    print(f"验证失败:\n  原始: {original_sign}\n  还原: {restored_sign}")

# 4. 多组测试
for i in range(10):
    test_params['t'] = int(time.time() * 1000)
    assert call_original_js(test_params) == my_algorithm(test_params)
```

### Q: 遇到反调试代码怎么办?

A: 常见反调试及绕过:
```javascript
// 1. debugger检测
// 绕过: Chrome Console -> 右键断点 -> Never pause here

// 2. DevTools检测 (window.outerHeight)
// 绕过: 使用Playwright无头模式 + CDP

// 3. 时间检测
// 绕过: Hook Date.now() 返回固定值

// 4. 函数toString检测
// 绕过: 使用Proxy拦截toString调用

// 5. Stack trace检测
// 绕过: 使用VM隔离执行
```

### Q: 代码太长,AST解析很慢怎么办?

A:
1. **定位关键代码**: 只分析签名函数附近的代码
2. **分段处理**: 将大文件拆分成多个小文件
3. **缓存结果**: 相同代码不要重复分析
4. **降低深度**: 设置 `analysis_depth=2`
5. **跳过反混淆**: 直接用混淆代码+补环境

---

## 变更历史

| 版本 | 日期 | 变更类型 | 说明 |
|------|------|----------|------|
| 1.2.0 | 2026-01-28 | enhancement | 完善文档:添加接口定义表格/错误码/Skill交互关系/使用示例/配置选项/诊断日志/AI自诊断检查点 |
| 1.1.0 | 2026-01-27 | feature | 添加WASM分析流程,补充企业级反爬系统分析 |
| 1.0.1 | 2026-01-26 | fix | 修正AST反混淆示例代码错误 |
| 1.0.0 | 2026-01-25 | initial | 初始版本,包含基础JS逆向流程 |

---

## 相关模块

- **上游**: [03-签名模块](03-signature.md) - 签名参数分析,调用本模块进行深度逆向
- **配合**: [02-反检测模块](02-anti-detection.md) - 环境检测绕过,处理反调试
- **下游**: [04-请求模块](04-request.md) - 携带签名请求,验证算法正确性
- **协调**: [16-战术模块](16-tactics.md) - 逆向失败时选择替代方案
