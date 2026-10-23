# PPE 专业文献查询平台

面向 **政治学（Politics）、经济学（Economics）、哲学（Philosophy）** 三个学科的专业文献检索网站。

- **在线访问**：https://gsyzuishuai666.github.io/ppe-literature/
- **本地打开**：直接双击 `index.html` 即可（单文件前端，无需服务器）
- **数据快照**：2026-10-23

## 功能

1. **热门文献**
   - 国际文献：OpenAlex 旗舰期刊 / JSTOR / Elsevier 精选期刊
   - 国内权威：国家哲学社会科学文献中心（NSSD）核心期刊、集刊、优先发布
   - 中文文献
2. **PPE 热点**：政治学 / 经济学 / 哲学领域的中文与国际新闻
3. **文献搜索**：OpenAlex / Crossref / DOAJ 三数据源联合检索
4. **推荐指数**：按引用速度、期刊权威度、时效性综合评分（0–100）
5. **筛选**：核心期刊、发表年限、最低引用数、文献类型（期刊 / 学位论文）

## 项目结构

| 文件 | 说明 |
|---|---|
| `index.html` | 网站全部前端代码（HTML + CSS + JS 单文件） |
| `nssd_data.js` | 国内权威文献数据，定义 `window.NSSD_DATA` 供页面 `<script>` 加载 |
| `nssd_data.json` | 同一份数据的 JSON 版本，供后续处理 |
| `ppe_nssd_crawler.py` | NSSD 国家哲学社会科学文献中心爬虫（公开接口） |
| `update_ppe_data.bat` | 本地定时任务调用的数据更新脚本 |

## 数据来源

全部使用合规公开接口，不破解验证码、不绕过访问控制：

- [国家哲学社会科学文献中心 NSSD](https://www.ncpssd.cn/) — 国内权威文献（爬虫预抓取）
- [OpenAlex](https://api.openalex.org/) — 国际文献元数据
- [Crossref](https://api.crossref.org/) — DOI 与期刊元数据
- [DOAJ](https://doaj.org/api/) — 开放获取期刊
- Google News RSS（经 rss2json 代理）— 领域新闻

## 更新国内数据

```bash
pip install -r requirements.txt

# 抓取三个学科各 1 页（约 3–4 分钟，限速 1.2s/请求）
python ppe_nssd_crawler.py --pages 1

# 只抓核心期刊流
python ppe_nssd_crawler.py --core-only
```

爬虫会重新生成 `nssd_data.json` 和 `nssd_data.js`。更新后提交并推送即可刷新线上数据：

```bash
git add nssd_data.json nssd_data.js
git commit -m "Update NSSD data"
git push
```

## 部署

本站为纯静态页面，通过 GitHub Pages 发布：仓库 `main` 分支根目录即站点根目录，推送后自动构建。

## 声明

本站仅聚合公开学术元数据，文献版权归原作者及原出版机构所有。NSSD 不收录学位论文。
