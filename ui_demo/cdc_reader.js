// Reads enough of the supported master-list layouts to prepare an internal review.
// It cannot prove that a workbook was approved by CDC or that a balance is current.
window.cdcMasterReader = (() => {
  const cell = (sheet, address) => String(sheet?.[address]?.w ?? sheet?.[address]?.v ?? "").trim();
  const number = value => {
    const cleaned = String(value ?? "").replace(/[^0-9.\-]/g, "");
    return cleaned && Number.isFinite(Number(cleaned)) ? Number(cleaned) : null;
  };
  const companyName = text => {
    const raw = String(text ?? "").replace(/^.*?COMPANY\s*[:：]\s*/i, "").replace(/^.*?ក្រុមហ៊ុនៈ\s*/i, "").trim();
    const end = raw.match(/\b(?:CO\.?\s*,?\s*LTD\.?|LIMITED)\b/i);
    return (end ? raw.slice(0, end.index + end[0].length) : raw).replace(/\s+/g, " ").trim();
  };
  const companyKey = value => companyName(value).toUpperCase().replace(/[^A-Z0-9]/g, "");
  function inspect(workbook) {
    const sheetName = workbook.SheetNames.find(name => {
      const sheet = workbook.Sheets[name];
      return /description/i.test(cell(sheet,"B5")) || /រាយមុខ/.test(cell(sheet,"B10"));
    }) || workbook.SheetNames[0];
    const sheet = workbook.Sheets[sheetName];
    const english = /description/i.test(cell(sheet,"B5")) && /unit/i.test(cell(sheet,"F5"));
    const khmer = /រាយមុខ/.test(cell(sheet,"B10")) && /ឯកតា/.test(cell(sheet,"C10"));
    const cutStock = english && /ENDING/i.test(cell(sheet,"AC5"));
    const layout = cutStock ? "2026 cut-stock" : english ? "2026 application" : khmer ? "2025 quarterly" : "Unknown";
    const detectedCompany = companyName(english ? cell(sheet,"D1") || cell(sheet,"F1") || cell(sheet,"M1") : cell(sheet,"A2"));
    const headerText = english ? [cell(sheet,"D4"),cell(sheet,"F3"),cell(sheet,"A1")].join(" ") : [cell(sheet,"G6"),cell(sheet,"G7")].join(" ");
    const qipMatch = headerText.match(/QIP\s*[-#.: ]*([A-Z0-9/.-]+)/i) || headerText.match(/(?:CIB\s*(?:FILE\s*)?NO\.?\s*)[:# ]*([A-Z0-9/.-]+)/i);
    const qip = /\d/.test(qipMatch?.[1] || "") ? qipMatch[1] : "";
    const range = window.XLSX.utils.decode_range(sheet?.["!ref"] || "A1");
    const items = [];
    if (english || khmer) for (let row = english ? 6 : 11; row <= range.e.r && items.length < 1000; row++) {
      const excelRow = row + 1;
      const description = cell(sheet,`B${excelRow}`);
      const unit = cell(sheet,`${english ? "F" : "C"}${excelRow}`);
      const approved = number(cell(sheet,`${english ? "G" : "D"}${excelRow}`));
      if (!description || !unit || approved === null) continue;
      items.push({ row: excelRow, description, unit, approved,
        remaining: cutStock ? number(cell(sheet,`AC${excelRow}`)) : khmer ? number(cell(sheet,`Q${excelRow}`)) : null });
    }
    const warnings = [];
    if (layout === "Unknown") warnings.push("Workbook headings do not match a supported master-list layout.");
    if (!detectedCompany) warnings.push("Company name was not detected in the workbook.");
    if (!qip) warnings.push("QIP or CIB reference was not detected; enter and verify it manually.");
    if (khmer) warnings.push("Quarterly balance layout: confirm it corresponds to the approved master list and period.");
    if (!items.length) warnings.push("No master-list items were detected.");
    return { sheetName, layout, detectedCompany, qip, itemCount: items.length, items, warnings,
      structureOk: layout !== "Unknown" && items.length > 0 && Boolean(detectedCompany) };
  }
  async function read(file) {
    if (!/\.xlsx?$/i.test(file.name)) throw new Error("Choose an XLS or XLSX master-list workbook.");
    if (!window.XLSX) throw new Error("Excel reader is unavailable.");
    return inspect(window.XLSX.read(await file.arrayBuffer()));
  }
  return { read, inspect, companyKey };
})();
