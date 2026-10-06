/** Render the same daily sheets shown in the app, one Letter page per day. */
export async function exportLogsPdf(
  sheetContainer: HTMLElement,
  firstDate: string,
  lastDate: string,
) {
  // Load PDF libraries only when the user requests an export.
  const [{ default: html2canvas }, { jsPDF }] = await Promise.all([
    import('html2canvas'),
    import('jspdf'),
  ]);
  await document.fonts.ready;

  const sheets = Array.from(sheetContainer.querySelectorAll<HTMLElement>('.daily-log-sheet'));
  if (!sheets.length) throw new Error('Generate a trip before downloading its daily logs.');

  const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'letter', compress: true });
  pdf.setProperties({
    title: `Driver daily logs ${firstDate} to ${lastDate}`,
    creator: 'Spotter Trip Planner',
  });
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const marginMillimeters = 9;
  const availableWidth = pageWidth - marginMillimeters * 2;
  const availableHeight = pageHeight - marginMillimeters * 2 - 6;

  for (const [sheetIndex, sheet] of sheets.entries()) {
    const canvas = await html2canvas(sheet, {
      scale: 2,
      backgroundColor: '#ffffff',
      logging: false,
      windowWidth: 1200,
      scrollX: 0,
      scrollY: 0,
      // The map is unrelated to the sheet and must not be fetched for PDF rendering.
      ignoreElements: (element) => element.classList.contains('app-shell'),
      onclone: (clonedDocument) => {
        const clonedSheets = clonedDocument.querySelector<HTMLElement>('.print-logs');
        if (!clonedSheets) throw new Error('Daily sheets are not available for export.');
        // Reveal only the cloned sheets. The user's visible page stays unchanged.
        Object.assign(clonedSheets.style, {
          display: 'block',
          width: '1000px',
          position: 'absolute',
          left: '0',
          top: '0',
        });
      },
    });
    if (!canvas.width || !canvas.height)
      throw new Error('Could not render the daily sheet. Please try again.');
    const millimetersPerPixel = Math.min(
      availableWidth / canvas.width,
      availableHeight / canvas.height,
    );
    const imageWidth = canvas.width * millimetersPerPixel;
    const imageHeight = canvas.height * millimetersPerPixel;
    if (sheetIndex > 0) pdf.addPage();
    pdf.addImage(
      canvas,
      'PNG',
      (pageWidth - imageWidth) / 2,
      marginMillimeters,
      imageWidth,
      imageHeight,
      undefined,
      'FAST',
    );
    pdf.setFontSize(8);
    pdf.setTextColor(100);
    pdf.text(
      `Day ${sheetIndex + 1} of ${sheets.length} - Unsigned planning estimate`,
      pageWidth / 2,
      pageHeight - marginMillimeters,
      { align: 'center' },
    );
    canvas.width = 0;
    canvas.height = 0;
  }
  return pdf.output('blob');
}
