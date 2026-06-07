import type { CategoryMeta, NewsArticle } from "@/types/news";

export const reportMeta = {
  date: "2026-06-07",
  edition: "Morning Brief · Mock Preview",
  coreTopic: {
    zh: "AI 基础设施投资正在重塑科技公司的竞争边界",
    en: "AI infrastructure investment is reshaping the competitive edge of tech companies",
  },
  overview: {
    zh: "今日重点集中在 AI 算力、全球市场波动与大型体育赛事。以下内容为前端演示数据，暂未连接真实后端。",
    en: "Today’s focus spans AI compute, global market volatility, and major sports events. This is frontend demo data and is not connected to the live backend yet.",
  },
};

export const categories: CategoryMeta[] = [
  {
    key: "technology",
    label: { zh: "科技", en: "Technology" },
    accent: "bg-[#d97706]",
  },
  {
    key: "finance",
    label: { zh: "财经", en: "Finance" },
    accent: "bg-[#0f766e]",
  },
  {
    key: "sports",
    label: { zh: "体育", en: "Sports" },
    accent: "bg-[#2563eb]",
  },
  {
    key: "politics",
    label: { zh: "政治", en: "Politics" },
    accent: "bg-[#7c3aed]",
  },
  {
    key: "society",
    label: { zh: "社会", en: "Society" },
    accent: "bg-[#be123c]",
  },
];

export const articles: NewsArticle[] = [
  {
    slug: "ai-infrastructure-race",
    category: "technology",
    title: {
      zh: "AI 基础设施竞赛从芯片延伸到能源与数据中心",
      en: "The AI infrastructure race expands from chips to energy and data centers",
    },
    summary: {
      zh: "大型科技公司继续提高算力投资，竞争焦点开始覆盖电力、网络与数据中心效率。",
      en: "Major technology companies are increasing compute investment as competition spreads to power, networking, and data-center efficiency.",
    },
    fullSummary: {
      zh: "多家大型科技公司正在同步扩大 AI 基础设施预算。除了先进芯片，能源供应、机房选址、网络带宽和推理效率也成为决定部署速度的关键变量。",
      en: "Several major technology companies are expanding AI infrastructure budgets. Beyond advanced chips, energy supply, site selection, network capacity, and inference efficiency are becoming critical deployment constraints.",
    },
    whyItMatters: {
      zh: "这意味着 AI 竞争不再只是模型能力之争，而是资本、供应链和工程执行能力的综合较量。",
      en: "AI competition is no longer only about model quality; it is increasingly a contest of capital, supply chains, and engineering execution.",
    },
    background: {
      zh: "生成式 AI 的训练和推理都需要大量计算资源。随着用户规模上升，推理成本和电力需求的重要性正在快速增加。",
      en: "Training and serving generative AI require substantial compute. As usage grows, inference cost and power demand are becoming more important.",
    },
    beginnerExplanation: {
      zh: "可以把 AI 公司想象成新型工厂：芯片是机器，数据中心是厂房，电力是原料。只有三者同时到位，模型才能稳定服务更多用户。",
      en: "Think of an AI company as a new kind of factory: chips are the machines, data centers are the buildings, and electricity is the raw material. All three must scale together.",
    },
    source: "TechWire Demo",
    publishedAt: "08:35",
    score: 9.2,
    tags: ["AI", "半导体", "数据中心"],
    relatedLinks: [
      {
        label: { zh: "基础设施投资说明", en: "Infrastructure investment note" },
        url: "https://example.com/ai-infrastructure",
      },
      {
        label: { zh: "数据中心能耗背景", en: "Data-center energy background" },
        url: "https://example.com/data-center-energy",
      },
    ],
  },
  {
    slug: "chip-supply-chain",
    category: "technology",
    title: {
      zh: "先进封装成为 AI 芯片供应链的新瓶颈",
      en: "Advanced packaging becomes a new bottleneck in the AI chip supply chain",
    },
    summary: {
      zh: "需求增长让市场注意力从单一芯片产能转向封装、内存与高速互连。",
      en: "Rising demand shifts attention from chip capacity alone to packaging, memory, and high-speed interconnects.",
    },
    fullSummary: {
      zh: "AI 芯片的交付能力取决于多个供应链环节。先进封装、高带宽内存和高速网络设备如果不能同步扩产，最终系统产能仍会受到限制。",
      en: "AI chip delivery depends on several supply-chain layers. Without synchronized growth in packaging, high-bandwidth memory, and networking, overall system capacity remains constrained.",
    },
    whyItMatters: {
      zh: "供应链瓶颈会影响新产品交付、云服务成本和半导体行业利润分配。",
      en: "Supply constraints can influence product delivery, cloud costs, and how semiconductor profits are distributed.",
    },
    background: {
      zh: "现代 AI 加速器通常由多个芯片与内存模块组合，封装技术决定它们能否高效协作。",
      en: "Modern AI accelerators combine multiple chips and memory modules, and packaging determines how efficiently they work together.",
    },
    beginnerExplanation: {
      zh: "这像组装一支赛车队：不只是发动机要快，轮胎、传动和维修体系也必须跟得上。",
      en: "It is like building a racing team: a fast engine is not enough; tires, transmission, and maintenance must keep pace.",
    },
    source: "Semiconductor Daily Demo",
    publishedAt: "07:50",
    score: 8.6,
    tags: ["芯片", "供应链", "先进封装"],
    relatedLinks: [],
  },
  {
    slug: "global-market-volatility",
    category: "finance",
    title: {
      zh: "利率预期变化放大全球科技股波动",
      en: "Shifting rate expectations amplify volatility in global technology stocks",
    },
    summary: {
      zh: "市场重新评估降息节奏，高估值板块对长期利率变化更敏感。",
      en: "Markets are reassessing the pace of rate cuts, making high-valuation sectors more sensitive to long-term yields.",
    },
    fullSummary: {
      zh: "债券收益率与政策预期变化推动全球成长股出现更大波动。市场同时关注企业盈利能否覆盖高投入周期。",
      en: "Changes in bond yields and policy expectations are driving larger swings in global growth stocks. Investors are also watching whether earnings can support heavy investment cycles.",
    },
    whyItMatters: {
      zh: "科技股权重较高，波动可能传导到主要指数、养老金配置和市场风险偏好。",
      en: "Technology stocks carry significant index weight, so volatility can affect major benchmarks, pension allocations, and risk appetite.",
    },
    background: {
      zh: "利率越高，未来利润折算到今天的价值通常越低，因此成长股估值更容易受到影响。",
      en: "Higher rates generally reduce the present value of future profits, making growth-stock valuations more sensitive.",
    },
    beginnerExplanation: {
      zh: "可以把股票估值理解为对未来收入的提前报价。当资金成本上升，市场愿意提前支付的价格往往会下降。",
      en: "A stock valuation is a price paid today for future earnings. When money becomes more expensive, investors tend to pay less upfront.",
    },
    source: "Market Lens Demo",
    publishedAt: "08:12",
    score: 8.4,
    tags: ["美股", "利率", "科技股"],
    relatedLinks: [],
  },
  {
    slug: "asia-consumer-demand",
    category: "finance",
    title: {
      zh: "亚洲消费数据出现分化，企业下调短期预测",
      en: "Asian consumer data diverges as companies trim short-term forecasts",
    },
    summary: {
      zh: "不同市场的消费恢复速度差异扩大，企业更谨慎地管理库存与促销。",
      en: "Consumer recovery varies across markets, prompting more cautious inventory and promotion strategies.",
    },
    fullSummary: {
      zh: "部分市场的服务消费保持韧性，但可选商品需求恢复较慢。企业正在降低库存风险，并把预算集中到回报更明确的渠道。",
      en: "Services spending remains resilient in some markets while discretionary goods recover more slowly. Companies are reducing inventory risk and focusing budgets on clearer returns.",
    },
    whyItMatters: {
      zh: "消费变化会影响零售、物流、广告和制造业订单。",
      en: "Changes in consumption affect retail, logistics, advertising, and manufacturing orders.",
    },
    background: {
      zh: "消费数据通常是观察经济活力和居民信心的重要指标。",
      en: "Consumer data is a common indicator of economic activity and household confidence.",
    },
    beginnerExplanation: {
      zh: "当消费者更谨慎时，企业会少进货、少扩张，也会更频繁地调整价格和促销。",
      en: "When consumers become cautious, companies order less inventory, slow expansion, and adjust pricing more often.",
    },
    source: "Asia Business Demo",
    publishedAt: "06:48",
    score: 7.3,
    tags: ["亚洲", "消费", "零售"],
    relatedLinks: [],
  },
  {
    slug: "championship-final",
    category: "sports",
    title: {
      zh: "总决赛关键战进入最后阶段，核心球员健康成为焦点",
      en: "Championship series enters a decisive stretch with player health in focus",
    },
    summary: {
      zh: "系列赛走势胶着，球队轮换深度和核心球员恢复情况可能决定结果。",
      en: "The series remains close, with roster depth and the recovery of key players likely to decide the outcome.",
    },
    fullSummary: {
      zh: "双方在前几场比赛中展现出不同的节奏控制方式。随着赛程推进，伤病管理、替补得分和关键回合执行成为主要观察点。",
      en: "The teams have shown different approaches to tempo control. As the series progresses, injury management, bench scoring, and late-game execution are key factors.",
    },
    whyItMatters: {
      zh: "重大赛事结果会影响球队阵容决策、球员评价和商业关注度。",
      en: "Major championship outcomes influence roster decisions, player evaluations, and commercial attention.",
    },
    background: {
      zh: "长系列赛会不断放大阵容短板，球队通常需要根据对手调整轮换和防守策略。",
      en: "Long playoff series expose roster weaknesses and force teams to adjust rotations and defensive schemes.",
    },
    beginnerExplanation: {
      zh: "季后赛像连续下很多盘棋：上一场有效的办法，下一场可能就会被对手破解。",
      en: "A playoff series is like playing several chess games in a row: a winning tactic can be countered in the next match.",
    },
    source: "Sports Desk Demo",
    publishedAt: "09:05",
    score: 8.1,
    tags: ["总决赛", "伤病", "排名"],
    relatedLinks: [],
  },
  {
    slug: "tennis-ranking-shift",
    category: "sports",
    title: {
      zh: "新生代球员连续突破，网球排名竞争升温",
      en: "Rising players break through as the tennis ranking race tightens",
    },
    summary: {
      zh: "多位年轻球员在重要赛事取得突破，年终排名竞争提前进入关键期。",
      en: "Several younger players have made deep runs in major events, intensifying the year-end ranking race.",
    },
    fullSummary: {
      zh: "近期赛事结果让排名积分更加集中。接下来的草地和硬地赛季可能显著影响种子席位与年终总决赛资格。",
      en: "Recent results have compressed the rankings. The coming grass and hard-court seasons could reshape seedings and year-end qualification.",
    },
    whyItMatters: {
      zh: "排名决定重要赛事种子位置，也会影响赞助曝光与赛程选择。",
      en: "Rankings determine seeding and influence sponsorship exposure and scheduling choices.",
    },
    background: {
      zh: "职业网球排名按过去 52 周积分滚动计算，球员需要不断保住去年同期积分。",
      en: "Professional tennis rankings use a rolling 52-week points system, requiring players to defend prior results.",
    },
    beginnerExplanation: {
      zh: "排名积分像一张会过期的成绩单：去年拿到的分数到期后，必须靠今年的新成绩补回来。",
      en: "Ranking points are like grades that expire: last year’s points must be replaced by new results.",
    },
    source: "Court Watch Demo",
    publishedAt: "07:20",
    score: 7.6,
    tags: ["网球", "排名", "新生代"],
    relatedLinks: [],
  },
  {
    slug: "digital-policy-framework",
    category: "politics",
    title: {
      zh: "多国讨论生成式 AI 治理框架与透明度要求",
      en: "Governments discuss generative AI governance and transparency rules",
    },
    summary: {
      zh: "政策讨论聚焦模型风险披露、内容标记和关键行业使用边界。",
      en: "Policy discussions focus on risk disclosure, content labeling, and limits for high-impact sectors.",
    },
    fullSummary: {
      zh: "监管机构正在尝试在创新与安全之间建立可执行的规则。企业关注合规成本、跨境差异和开源模型的适用范围。",
      en: "Regulators are working to create enforceable rules that balance innovation and safety. Companies are watching compliance cost, cross-border differences, and open-model treatment.",
    },
    whyItMatters: {
      zh: "治理规则可能改变产品上线速度、数据使用方式和企业责任边界。",
      en: "Governance rules may change product launch timelines, data practices, and corporate liability.",
    },
    background: {
      zh: "生成式 AI 可以快速生成文本、图片和代码，因此政策制定者担心误导内容、隐私与关键系统风险。",
      en: "Generative AI can rapidly produce text, images, and code, raising concerns about misinformation, privacy, and critical systems.",
    },
    beginnerExplanation: {
      zh: "政策目标类似给新型交通工具制定道路规则：既要允许它发展，也要明确发生事故时谁负责。",
      en: "The policy goal is like writing traffic rules for a new vehicle: allow progress while defining responsibility when things go wrong.",
    },
    source: "Policy Brief Demo",
    publishedAt: "06:30",
    score: 8.0,
    tags: ["AI 治理", "政策", "透明度"],
    relatedLinks: [],
  },
  {
    slug: "trade-dialogue",
    category: "politics",
    title: {
      zh: "区域贸易对话重启，供应链稳定成为首要议题",
      en: "Regional trade talks resume with supply-chain stability at the top of the agenda",
    },
    summary: {
      zh: "各方希望降低关键商品贸易摩擦，但具体执行安排仍需后续协商。",
      en: "Participants aim to reduce friction around critical goods, though implementation details remain under negotiation.",
    },
    fullSummary: {
      zh: "会议重点围绕关税、关键原材料与跨境投资审查。当前公开信息表明对话恢复，但尚不足以判断最终协议范围。",
      en: "Talks center on tariffs, critical materials, and investment screening. Public information confirms renewed dialogue but not the final scope of an agreement.",
    },
    whyItMatters: {
      zh: "贸易规则会影响制造成本、商品价格与企业选址。",
      en: "Trade rules affect manufacturing costs, consumer prices, and corporate location decisions.",
    },
    background: {
      zh: "过去几年企业通过增加供应商和调整库存降低单一地区风险。",
      en: "In recent years, companies have diversified suppliers and adjusted inventories to reduce geographic concentration risk.",
    },
    beginnerExplanation: {
      zh: "贸易谈判就像重新协商跨国运输规则，费用和限制的细小变化也可能影响最终商品价格。",
      en: "Trade talks are like renegotiating international shipping rules: small fee or restriction changes can affect final prices.",
    },
    source: "World Affairs Demo",
    publishedAt: "05:55",
    score: 7.5,
    tags: ["贸易", "供应链", "政策"],
    relatedLinks: [],
  },
  {
    slug: "urban-heat-response",
    category: "society",
    title: {
      zh: "城市高温应对从预警转向社区级韧性建设",
      en: "Urban heat response shifts from alerts to neighborhood resilience",
    },
    summary: {
      zh: "多地开始增加公共降温空间，并针对老人和户外工作者提供更细化服务。",
      en: "Cities are expanding cooling spaces and targeted services for older residents and outdoor workers.",
    },
    fullSummary: {
      zh: "传统高温预警正在与社区服务结合，包括延长公共设施开放时间、改善绿荫和建立高风险人群联系机制。",
      en: "Heat alerts are increasingly paired with community services, longer public-facility hours, more shade, and outreach to vulnerable residents.",
    },
    whyItMatters: {
      zh: "极端高温会直接影响健康、劳动效率和城市用电峰值。",
      en: "Extreme heat directly affects health, productivity, and peak electricity demand.",
    },
    background: {
      zh: "高密度城区的建筑和路面会储存热量，使夜间降温更慢。",
      en: "Dense urban buildings and paved surfaces store heat, slowing nighttime cooling.",
    },
    beginnerExplanation: {
      zh: "城市像一块白天晒热的石头，晚上也不会立刻变凉，因此社区需要更具体的避暑安排。",
      en: "A city can behave like a stone heated all day: it stays warm at night, so neighborhoods need practical cooling plans.",
    },
    source: "City Lab Demo",
    publishedAt: "08:00",
    score: 7.8,
    tags: ["城市", "高温", "公共健康"],
    relatedLinks: [],
  },
  {
    slug: "education-ai-literacy",
    category: "society",
    title: {
      zh: "学校把 AI 素养纳入课程，重点转向验证与引用",
      en: "Schools add AI literacy with an emphasis on verification and citation",
    },
    summary: {
      zh: "新课程不只教授工具使用，还强调来源核验、隐私和学术诚信。",
      en: "New curricula go beyond tool use to emphasize source checking, privacy, and academic integrity.",
    },
    fullSummary: {
      zh: "教育机构正在尝试建立适合不同年龄段的 AI 使用规范。课堂重点逐渐从禁止工具转向理解工具限制并验证输出。",
      en: "Education systems are developing age-appropriate AI guidelines. Classrooms are shifting from blanket bans toward understanding limitations and checking outputs.",
    },
    whyItMatters: {
      zh: "AI 工具会改变学习方式，也会重新定义教师评价与学生独立完成作业的边界。",
      en: "AI tools change how students learn and reshape the boundary between assistance and independent work.",
    },
    background: {
      zh: "大模型可能生成流畅但不准确的内容，因此引用与交叉核验成为基础能力。",
      en: "Language models can produce fluent but inaccurate content, making citation and cross-checking essential skills.",
    },
    beginnerExplanation: {
      zh: "AI 更像一个反应很快但偶尔会答错的学习伙伴，使用者仍然需要检查它说的内容。",
      en: "AI is like a fast study partner that can still be wrong, so users must verify what it says.",
    },
    source: "Education Review Demo",
    publishedAt: "07:10",
    score: 7.4,
    tags: ["教育", "AI 素养", "隐私"],
    relatedLinks: [],
  },
];

export const categoryChartData = [
  { category: "科技", count: 18, fill: "var(--color-technology)" },
  { category: "财经", count: 14, fill: "var(--color-finance)" },
  { category: "体育", count: 10, fill: "var(--color-sports)" },
  { category: "政治", count: 8, fill: "var(--color-politics)" },
  { category: "社会", count: 12, fill: "var(--color-society)" },
];

export const importanceTrendData = [
  { day: "06/01", high: 7, average: 6.8 },
  { day: "06/02", high: 9, average: 7.1 },
  { day: "06/03", high: 6, average: 6.4 },
  { day: "06/04", high: 11, average: 7.5 },
  { day: "06/05", high: 8, average: 6.9 },
  { day: "06/06", high: 10, average: 7.3 },
  { day: "06/07", high: 12, average: 7.7 },
];

export const sourceShareData = [
  { key: "techwire", name: "TechWire", value: 28 },
  { key: "market", name: "Market Lens", value: 24 },
  { key: "world", name: "World Affairs", value: 18 },
  { key: "sportsdesk", name: "Sports Desk", value: 16 },
  { key: "others", name: "Others", value: 14 },
];

export const getArticle = (slug: string) =>
  articles.find((article) => article.slug === slug);
