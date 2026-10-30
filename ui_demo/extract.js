// Small, transparent parser for the supplier invoice / packing-list layout used in this demo.
// It reads displayed cell values. Unknown layouts remain reviewable rather than inventing data.
window.importExtractor = (() => {
  const value = (rows, row, col) => String(rows?.[row]?.[col] ?? "").trim();
  const number = raw => {
    const cleaned = String(raw ?? "").replace(/[^0-9.\-]/g, "");
    return cleaned && Number.isFinite(Number(cleaned)) ? Number(cleaned) : null;
  };
  const nonemptyAfter = (row, start) => (row || []).slice(start).map(x => String(x ?? "").trim()).find(Boolean) || "";
  const labeled = (rows, pattern) => {
    for (const row of rows || []) for (let col = 0; col < row.length; col++) {
      if (pattern.test(String(row[col] ?? ""))) return nonemptyAfter(row, col + 1);
    }
    return "";
  };
  const findHeader = rows => rows.findIndex(row => row.some(cell => /H\.?S\.?\s*Code/i.test(String(cell ?? ""))) && row.some(cell => /Quantity/i.test(String(cell ?? ""))));
  const lines = (rows, packing) => {
    const header = findHeader(rows);
    if (header < 0) return { items: [], totalRow: [] };
    const items = [];
    let totalRow = [];
    for (let i = header + (packing && /Kgs/i.test((rows[header + 1] || []).join(" ")) ? 2 : 1); i < Math.min(rows.length, header + 100); i++) {
      const row = rows[i] || [];
      const quantity = number(row[3]);
      if (quantity === null || !String(row[0] ?? "").trim()) { totalRow = row; if (items.length) break; continue; }
      items.push({
        row: i + 1, hsCode: value(rows, i, 0), chinese: value(rows, i, 1), english: value(rows, i, 2),
        quantity, unit: value(rows, i, 4),
        ...(packing ? { packages: number(row[5]), grossWeight: number(row[6]), netWeight: number(row[7]), volume: number(row[8]) }
          : { unitPrice: number(row[5]), amount: number(row[6]) })
      });
    }
    return { items, totalRow };
  };
  const sheetFor = (attachments, kind) => {
    const preferred = attachments?.[kind]?.type === "sheet" ? attachments[kind].sheets : [];
    const other = Object.entries(attachments || {}).filter(([key]) => key !== kind).flatMap(([,a]) => a?.type === "sheet" ? a.sheets : []);
    const all = [...preferred, ...other];
    const match = sheets => sheets.find(sheet => kind === "invoice" ? /invoice/i.test(sheet.name) : /pack/i.test(sheet.name))
      || sheets.find(sheet => (sheet.rows || []).slice(0, 8).flat().some(cell =>
        kind === "invoice" ? /commercial invoice/i.test(String(cell)) : /packing list/i.test(String(cell))));
    return match(preferred) || match(all);
  };
  const header = rows => {
    const destinationRow = rows.find(row => row.some(cell => /Destination\s*:/i.test(String(cell ?? "")))) || [];
    const destinationCol = destinationRow.findIndex(cell => /Destination\s*:/i.test(String(cell ?? "")));
    const fromCol = destinationRow.findIndex(cell => /From\s*:/i.test(String(cell ?? "")));
    const originParts = fromCol >= 0 ? destinationRow.slice(fromCol + 1).filter(Boolean) : destinationRow.slice(3).filter(Boolean);
    return {
      supplier: value(rows, 0, 0),
      company: labeled(rows.slice(0, 10), /To\s*:\s*Messers/i),
      contract: labeled(rows.slice(0, 12), /Contract\s*No/i),
      destination: destinationCol >= 0 ? nonemptyAfter(destinationRow.slice(0, fromCol >= 0 ? fromCol : 3), destinationCol + 1) : "",
      origin: originParts.join(" ").trim(),
    };
  };
  function extract(attachments) {
    const invoiceSheet = sheetFor(attachments, "invoice");
    const packingSheet = sheetFor(attachments, "packing");
    const invoiceRows = invoiceSheet?.rows || [];
    const packingRows = packingSheet?.rows || [];
    const invoiceHeader = header(invoiceRows);
    const packingHeader = header(packingRows);
    const invoiceData = lines(invoiceRows, false);
    const packingData = lines(packingRows, true);
    const invoiceTotal = number(invoiceData.totalRow[6]);
    const amount = invoiceTotal ?? (invoiceData.items.length ? invoiceData.items.reduce((sum, item) => sum + (item.amount || 0), 0) : null);
    const result = {
      invoiceSheet: invoiceSheet?.name || "", packingSheet: packingSheet?.name || "",
      invoiceNo: labeled(invoiceRows.slice(0, 10), /Invoice\s*No/i),
      invoiceDate: labeled(invoiceRows.slice(0, 10), /^Date\s*:/i),
      supplier: invoiceHeader.supplier || packingHeader.supplier,
      company: invoiceHeader.company || packingHeader.company,
      contract: invoiceHeader.contract || packingHeader.contract,
      origin: invoiceHeader.origin || packingHeader.origin,
      destination: invoiceHeader.destination || packingHeader.destination,
      currency: /USD|US DOLLARS/i.test(invoiceRows.flat().join(" ")) ? "USD" : "",
      amount,
      quantity: number(invoiceData.totalRow[3]) ?? (invoiceData.items.length ? invoiceData.items.reduce((sum, item) => sum + item.quantity, 0) : null),
      packages: number(packingData.totalRow[5]) ?? (packingData.items.length ? packingData.items.reduce((sum, item) => sum + (item.packages || 0), 0) : null),
      grossWeight: number(packingData.totalRow[6]) ?? (packingData.items.length ? packingData.items.reduce((sum, item) => sum + (item.grossWeight || 0), 0) : null),
      netWeight: number(packingData.totalRow[7]) ?? (packingData.items.length ? packingData.items.reduce((sum, item) => sum + (item.netWeight || 0), 0) : null),
      volume: number(packingData.totalRow[8]) ?? (packingData.items.length ? packingData.items.reduce((sum, item) => sum + (item.volume || 0), 0) : null),
      invoiceLines: invoiceData.items, packingLines: packingData.items, issues: []
    };
    if (!invoiceSheet) result.issues.push("Invoice sheet not detected");
    if (!packingSheet) result.issues.push("Packing list sheet not detected");
    if (invoiceSheet && !result.invoiceNo) result.issues.push("Invoice number needs entry");
    if (invoiceSheet && !invoiceData.items.length) result.issues.push("Invoice item lines not detected");
    if (packingSheet && !packingData.items.length) result.issues.push("Packing item lines not detected");
    if (invoiceHeader.company && packingHeader.company && invoiceHeader.company !== packingHeader.company) result.issues.push("Consignee differs between invoice and packing list");
    if (invoiceHeader.contract && packingHeader.contract && invoiceHeader.contract !== packingHeader.contract) result.issues.push("Contract reference differs between documents");
    if (invoiceData.items.length && packingData.items.length) {
      if (invoiceData.items.length !== packingData.items.length) result.issues.push("Item line counts differ between documents");
      const packingQuantity = number(packingData.totalRow[3]) ?? packingData.items.reduce((sum, item) => sum + item.quantity, 0);
      if (result.quantity !== null && result.quantity !== packingQuantity) result.issues.push("Invoice and packing total quantities differ");
      for (let i = 0; i < Math.min(invoiceData.items.length, packingData.items.length); i++) {
        const inv = invoiceData.items[i], pack = packingData.items[i];
        if (inv.quantity !== pack.quantity || inv.unit.toUpperCase() !== pack.unit.toUpperCase()) result.issues.push(`Line ${i + 1}: invoice and packing quantity or unit differ`);
        if (inv.hsCode !== pack.hsCode || inv.chinese !== pack.chinese) result.issues.push(`Line ${i + 1}: item identity differs between documents`);
      }
    }
    const translationMap = new Map();
    for (const item of invoiceData.items) {
      const english = item.english.toLowerCase();
      if (english && translationMap.has(english) && translationMap.get(english) !== item.chinese) {
        result.issues.push(`English “${item.english}” is used for different Chinese items; verify translation`);
        translationMap.delete(english);
      } else if (english) translationMap.set(english, item.chinese);
    }
    if (invoiceTotal !== null && invoiceData.items.length) {
      const lineTotal = invoiceData.items.reduce((sum, item) => sum + (item.amount || 0), 0);
      if (Math.abs(invoiceTotal - lineTotal) > 0.01) result.issues.push("Invoice total does not equal the item subtotals");
    }
    return result;
  }
  return { extract };
})();
