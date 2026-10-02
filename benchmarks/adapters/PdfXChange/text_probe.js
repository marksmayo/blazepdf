// Non-mutating PDF-XChange Editor benchmark probe.
// The host binds `this` to the supplied PDF document.
try {
    var total = 0;
    for (var page = 0; page < this.numPages; page++) {
        total += this.getPageNumWords(page);
    }
    console.println("BLAZEPDF_PXC_WORDS=" + total);
} catch (error) {
    console.println("BLAZEPDF_PXC_ERROR=" + error);
}
