🌐 [English](README.md) | 中文

<div align="center">

# 🥷 SploitAgent

**为 AI 智能体打造的安全技能库。**
161 项进攻 + 防守技术,你的 AI 智能体按需加载,在**已授权**的目标上作业——从侦察到报告。

[![CI](https://github.com/NoorQureshi/SploitAgent/actions/workflows/ci.yml/badge.svg)](https://github.com/NoorQureshi/SploitAgent/actions/workflows/ci.yml)
![skills](https://img.shields.io/badge/skills-161-334155?style=flat-square)
![domains](https://img.shields.io/badge/domains-20-334155?style=flat-square)
![mapped](https://img.shields.io/badge/mapped-OWASP%20%C2%B7%20MITRE%20ATT%26CK-334155?style=flat-square)
![routing](https://img.shields.io/badge/routing-483%20trigger%20cases%20CI--verified-334155?style=flat-square)
![license](https://img.shields.io/badge/license-MIT-334155?style=flat-square)

<sub>[文档](https://noorqureshi.github.io/SploitAgent/) · [工作原理](https://noorqureshi.github.io/SploitAgent/interact.html) · [搜索技能](https://noorqureshi.github.io/SploitAgent/catalog.html) · [参与贡献](CONTRIBUTING.md)</sub>

</div>

> **如果你是 AI 智能体:** 阅读 [AGENTS.md](AGENTS.md)(或精简引导 [README_AI.md](README_AI.md))并严格遵循——这个仓库是设计来由你操作的,而不仅仅是供人阅读的。

<p align="center">
  <img src="docs/screenshots/demo.svg" width="820"
       alt="Terminal replay: Claude Code with SploitAgent skills solves 9 of 116 OWASP Juice Shop challenges in 10 minutes">
</p>

**实测基准,而非空口宣称。** 上方回放来自一次真实运行:目标是 OWASP Juice Shop(116 个挑战,本地运行),搭载这些技能的智能体在 **10 分钟内解出 9 个挑战**——SQLi 认证绕过、UNION 凭据拖库、XXE、JWT 算法混淆、BOLA——每一个都附有成文的漏洞发现。评分取自目标自身的解题日志,绝不采信智能体的一面之词。完整的 A/B 对比(有技能 vs 无技能)以及自行复现的方法,见 [bench/RESULTS.md](bench/RESULTS.md)。

## 这是什么

你的 AI 智能体是个很强的通才,但它并不知道某项具体工作的*确切方法*——比如测试 API 的访问控制缺陷。**SploitAgent 补上的正是这块短板:** 一册 161 页的"如何做好这一项技术"的简明手册,智能体需要哪页就翻到哪页。

它也不会取代你的工具箱:这些技能会教你的智能体何时、如何驱动你手上已有的工具——sqlmap、nmap、ffuf、nuclei、Burp Suite、Ghidra、Frida、hashcat、Impacket——包含每项工作所需的确切命令、后续动作和验证步骤。机器可读的路由表([`data/routing.json`](data/routing.json)——**483 条触发用例,CI 验证**)让任何智能体或集成都能确定性地选对技能,无需猜测提示词。

你用大白话描述任务 → 它挑出正确的技能页、执行、证实漏洞并写成报告 → 且绝不触碰你设定范围之外的任何东西。

## 选择你的入口

同一套技能库,五种进入方式。以下一切都在你的终端中运行——安装一次(快速开始),然后和你的智能体对话即可。

| 你是…… | 你输入…… | 智能体会做什么 |
|---|---|---|
| **漏洞赏金猎人** | "target.com 在我的项目范围内——评估它" | `tradecraft-scope-roe` 确认边界 → `recon-*` 绘制攻击面 → 攻击面清单驱动覆盖 → 确认的漏洞用 `reporting-bug-bounty-writeup` 写成可直接提交的报告,`tradecraft-duplicate-avoidance` 还会在你为已知重复类目白花时间之前给出提醒 |
| **CTF 选手** | "帮我解这道题"(web / pwn / crypto / rev) | 加载对应类别的技术页(`web-*`、`exploit-*`、`cryptography-*`、`reverse-engineering-*`),跑完整个变体矩阵,而不是一个 payload 失败就收手 |
| **渗透测试工程师** | "按我们签署的范围评估这个应用" | 用 `tradecraft-attack-scenarios` 制定计划,把清单当作**覆盖地图**逐项推进——每一类都标记为已证实、已排除(附尝试记录)或已跳过——然后用 `reporting-pentest-report` 写成报告 |
| **红队成员** | "我在这个 AD 域里已有立足点(已授权)" | `privesc-*` 负责提权,`ad-*`(Kerberoasting、ADCS、委派、DACL 滥用)负责横向移动,`network-pivoting-tunneling` 负责扩散,`tradecraft-attack-path-mapping` 让你看清整条攻击路径 |
| **蓝队 / 防守方** | "为这些攻击编写检测规则" | `defense-*` 覆盖检测工程、Sigma 规则、日志查询、应急响应分诊、加固——`defense-purple-team` 能把任何攻击技能变成一次检测测试,头部攻击技能还附带 `detection.md` 伴侣文档(Sigma 规则 + 日志源 + 误报调优) |

## 快速开始

> **需要:** 一个 AI 智能体——[Claude Code](https://claude.com/claude-code)、[OpenCode](https://opencode.ai)、Codex、Gemini,或你自己的 API 脚本——外加 `git` 和一个终端。`python3` 仅可选控制台需要。

```console
# 1 · install once — links the skills into your agent + puts `sploit` on PATH
$ git clone https://github.com/NoorQureshi/SploitAgent && cd SploitAgent
$ ./sploit install

# 2 · make a workspace for your target (anywhere) and set the boundary
$ sploit new acme.com ~/work/acme
$ cd ~/work/acme
$ nano scope.txt                     # your authorized target(s) — nothing else gets touched

# 3 · (optional) watch the agent work, live, in your browser
$ sploit watch                       # runs in the background · stop: sploit watch --stop

# 4 · open your agent in the workspace and describe the task   ↓ (Claude Code / OpenCode below)
```

**各部分如何配合:** 你的**终端**负责运行智能体;它做出的每个决策、尝试和证明都落在**工作区文件夹**里(`scope.txt · plan.md · notes.md · findings/`)——这是你可以阅读、diff、并交付给客户的事实源。任何智能体都是同样的流程,没有任何环节是 Claude 专属的。

## 用你的智能体运行

在**工作区内**打开你的智能体,用大白话描述任务——匹配的技能会自动加载。

<details open>
<summary><b>Claude Code</b></summary>

```console
~/work/acme $ claude          # skills are already in ~/.claude/skills — auto-discovered everywhere

> Start an authorized assessment of acme.com. Confirm scope, then recon.

  ● tradecraft-scope-roe        loaded · scope confirmed (*.acme.tld)
  ● recon-subdomain-enum        14 hosts · api.acme.tld live
  ● api-bola                    testing object references on /api/v1/orders
      ✓ cross-tenant read confirmed with 2 accounts
  ✔ wrote findings/idor-orders.md
```

`./sploit install` 已把技能链接到 `~/.claude/skills/`(并以同样方式接入了检测到的其他智能体),所以 Claude Code 能在**任何**文件夹中找到它们,并自动加载符合你请求的那一个。
</details>

<details>
<summary><b>OpenCode</b></summary>

```console
~/work/acme $ opencode        # launches the TUI in this folder, using your own model/API key

> Use the SploitAgent skills in ./skills. Start an authorized assessment of
  acme.com — confirm scope from scope.txt, then recon the attack surface.

  → reads AGENTS.md + ./skills · loads recon-* then routes by what it finds
```

无需安装步骤:OpenCode 会自动读取工作区里的 `AGENTS.md` 和 `./skills` 目录。(首次使用:`opencode auth login` 配置你的服务商 / API 密钥。)
</details>

<details>
<summary><b>Codex · Gemini · 任意其他智能体 / 你自己的 API 脚本</b></summary>

```console
~/work/acme $ codex           # or: gemini  — run inside the workspace

> Use the SploitAgent skills here. Start an authorized assessment of acme.com,
  confirm scope from scope.txt, then recon.
```

任何智能体都可以:让它读取工作区中的 `AGENTS.md` 和 `./skills`,或者把单个 `SKILL.md` 粘贴进对话做一次性任务。无需任何接线配置。
</details>

<details>
<summary><b>可选:在浏览器中实时观察智能体(<code>sploit watch</code>)</b></summary>

终端就是完整的工作流——但如果你想实时、**只读**地查看智能体在做什么,`sploit watch` 会在 `http://127.0.0.1:8787` 打开一个小型仪表盘。它只是读取磁盘上的工作区,所以无论你运行哪个智能体,表现都一致。

<p align="center">
  <img src="docs/screenshots/attack-map.png" width="820"
       alt="The console Attack Map: each attack lead with its status, the reasoning behind it, the steps taken, and a link to the confirmed finding">
</p>
<p align="center">
  <img src="docs/screenshots/finding.png" width="49%"
       alt="A confirmed finding rendered in the console: steps to reproduce, the request, and an impact table">
  &nbsp;
  <img src="docs/screenshots/activity.png" width="49%"
       alt="The live activity timeline: decisions, commands, results and findings as the agent works">
</p>

- **Attack Map(攻击地图)**——整个行动呈现为一张决策图:哪些已证实、已排除、受阻、跳过——以及*为什么*。
- **Findings(漏洞发现)**——每个确认的问题渲染完毕、可直接提交;**Activity(活动)**——带推理过程的实时可筛选时间线;**Plan / Notes(计划 / 笔记)**——策略与运行日志。

在 Claude Code 下,内置 hook 会自动记录命令,即使智能体不手动写日志,控制台也会被填满。
</details>

## 随意提问

| 你输入…… | 智能体加载 |
|---|---|
| "对 acme.com 做侦察并绘制攻击面" | `recon-*` |
| "测一下这个 API 有没有 IDOR / BOLA(我已授权)" | `api-bola`、`web-idor` |
| "这个登录的 JWT 能伪造吗?" | `web-auth-jwt` |
| "审查 ./src 里的注入类漏洞" | `code-review-*` |
| "我拿到 shell 了——接下来干嘛?" | `privesc-enumeration` |
| "把这个发现写成报告" | `reporting-*` |
| "写一条 Sigma 规则来检测这个" | `defense-detection-sigma` |

## 里面有什么

**161 个技能,横跨 20 个领域。** [🔎 搜索全部](https://noorqureshi.github.io/SploitAgent/catalog.html) · 或浏览 [CATALOG.md](CATALOG.md)。

`web` · `api` · `cloud` · `ad` · `network` · `wireless` · `recon` · `mobile` · `ai-ml` · `code-review` · `reverse-engineering` · `ctf` · `hardware` · `cryptography` · `exploit-dev` · `privesc` · `payloads` · `tools` · `defense` · `reporting` · `automation` · `tradecraft` · `social-eng`

<details>
<summary><b>查看每个领域的覆盖范围</b></summary>

| 领域 | # | 覆盖内容 |
|---|:--:|---|
| [`web`](skills/web) | 45 | XSS、SQLi、SSRF、SSTI、IDOR、XXE、CSRF、CORS、LFI、命令注入、反序列化、OAuth、SAML、请求走私、原型链污染、缓存投毒、缓存欺骗、Host 头攻击、点击劫持、CSP 绕过、DOM clobbering、HTTP 参数污染、postMessage、WebSocket、条件竞争、业务逻辑、文件上传、JWT、2FA/MFA 绕过、账户接管、依赖混淆、客户端签名逆向、认证会话处理、Python 沙箱逃逸、Cypher 注入、JDBC/连接串 RCE 、浏览器扩展逆向|
| [`ai-ml`](skills/ai-ml) | 11 | 提示注入、越狱、RAG 投毒、模型窃取、agent/工具与 MCP 滥用、不安全的输出处理、供应链、无限制资源消耗 、系统提示词泄露、敏感数据泄露|
| [`cloud`](skills/cloud) | 9 | IMDS 凭据窃取、对象存储暴露、Kubernetes、容器逃逸、暴露的 Docker/daemon API 滥用、IAM 提权、镜像仓库、GCP、Azure / Entra ID |
| [`api`](skills/api) | 9 | BOLA/BFLA、GraphQL、gRPC、批量赋值、认证攻击、模糊测试、版本漂移、NoSQL 注入 |
| [`recon`](skills/recon) | 9 | 子域名枚举、DNS 分析、内容与 JS 发现、OSINT、GitHub 代码泄露发现、云资产发现、服务枚举、技术栈指纹识别 |
| [`defense`](skills/defense) | 15 | 检测工程(流水线 + Sigma/ATT&CK)、威胁狩猎、事件响应、DFIR 分诊、网络检测(NSM)、云检测与响应、Active Directory 防御、恶意软件分诊、加固基线、威胁建模、日志分析、紫队演练 、威胁情报、深度取证分析|
| [`code-review`](skills/code-review) | 15 | 方法论、危险汇聚点(sink)目录、密钥检测、CI/CD 安全、IaC(Terraform/Ansible/K8s)、智能合约(Solidity)、Python、Node.js、PHP、Java/Spring、Go、Ruby/Rails、.NET/C#、C/C++、Rust |
| [`mobile`](skills/mobile) | 5 | Android 与 iOS 评估、证书固定绕过、deep-link 滥用、WebView 滥用 |
| [`ad`](skills/ad) | 5 | Kerberoasting / AS-REP、ADCS(ESC1–8)、ACL/DACL 滥用、Kerberos 委派滥用(RBCD / S4U / 胁迫→中继)、横向移动武器库 |
| [`network`](skills/network) | 8 | 服务攻击、横向与隧道、NTLM 胁迫与中继、密码喷洒与撞库、边界设备与 VPN 攻防、哈希与凭据破解 、邮件安全(钓鱼分析、SPF/DKIM/DMARC)、数据库安全评估|
| [`wireless`](skills/wireless) | 2 | WPA2-PSK 握手包/PMKID 捕获与破解、evil-twin / 恶意 AP 企业级(PEAP-MSCHAPv2)凭据收割 |
| [`privesc`](skills/privesc) | 4 | 立足点后的枚举与凭据搜寻、Linux 武器库、GTFOBins(sudo/SUID/capabilities)、Windows 令牌冒用 |
| [`exploit-dev`](skills/exploit-dev) | 3 | 漏洞链组合与影响放大、PoC 开发、内存破坏利用(ROP / 格式化字符串 / ret2libc) |
| [`reverse-engineering`](skills/reverse-engineering) | 3 | 原生二进制分诊、反混淆(加壳/JS/WASM/JSVMP)、固件提取与分析 |
| [`ctf`](skills/ctf) | 6 | CTF 方法论(10 分钟快速分诊)、web / pwn / crypto / rev / forensics 题型攻略 |
| [`tools`](skills/tools) | 11 | Metasploit、Burp Suite、nuclei、sqlmap、nmap、hashcat、hydra、ffuf、curl、MCP 工具桥接、工具选型 |
| [`cryptography`](skills/cryptography) | 2 | 弱/教科书式 RSA(JWT RS256、自研签名)、对称预言机(CBC padding、ECB、哈希长度扩展) |
| [`payloads`](skills/payloads) | 4 | WAF/过滤器绕过、XSS polyglot、反弹 shell 与 TTY 升级、文件传输 |
| [`reporting`](skills/reporting) | 6 | 漏洞分诊与验证、漏洞赏金报告撰写、渗透测试报告、CVSS/严重性评分、分诊沟通 、证据审查|
| [`automation`](skills/automation) | 3 | 侦察流水线、自定义 nuclei 模板 、浏览器自动化|
| [`tradecraft`](skills/tradecraft) | 9 | 范围与交战规则、攻击场景规划、攻击路径映射、跨技能的转向/决策、目标选择、重复规避、漏洞赏金平台情报、复杂多阶段行动 、杀伤链编排|
| [`social-eng`](skills/social-eng) | 4 | 已授权的人因测试:方法论、钓鱼、语音钓鱼/伪装话术、物理评估(仅限渗透测试) |

</details>

## 仅限授权使用

仅用于你**被允许**开展的安全工作——已签署的渗透测试范围、将目标列入范围的漏洞赏金项目,或你自有的系统。每次行动加载的第一个技能是 `tradecraft-scope-roe`:它确认授权,并拒绝任何不在你 `scope.txt` 之内的目标。如需报告 SploitAgent 本身的漏洞,请见 [SECURITY.md](SECURITY.md)。

## 参与贡献

一次贡献就是一个 Markdown 文件——不需要写代码:

```console
$ cp skills/_templates/technique.md skills/<domain>/<slug>/SKILL.md
$ python3 tools/catalog.py     # regenerate the indexes + stamp counts
$ ./tools/check.sh             # run everything CI runs, before you push
```

想要补充的技能方向:[ROADMAP.md](ROADMAP.md) · 完整指南:[CONTRIBUTING.md](CONTRIBUTING.md) · [行为准则](CODE_OF_CONDUCT.md)。

## 许可证

[MIT](LICENSE)。为授权安全工作而生。
