window.TS = window.TS || {};
TS.state = { token: localStorage.getItem("ts_token") || "", user: null, selectedCaseId: null, cases: [], latestRisk: {}, nextActions: {}, passport: null, page: "dashboard" };
TS.pages = [
  ["dashboard", "Dashboard"],
  ["cases", "Case Queue"],
  ["portfolio", "Portfolio Stress"],
  ["passport", "Risk Passport"],
  ["copilot", "Copilot Brief"],
  ["decision", "Decision & Settlement"],
  ["fraud", "Fraud Network"],
  ["audit", "Audit & Governance"],
  ["admin", "Admin / Debug"]
];
