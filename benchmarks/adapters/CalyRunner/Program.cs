using System.Diagnostics;
using System.Text;
using System.Text.Json;
using Caly.Pdf;
using Caly.Pdf.Models;
using Caly.Pdf.PageFactories;
using UglyToad.PdfPig;

var (mode, path) = args switch
{
    [var pdf] => ("first-page", pdf),
    ["--inspect", var pdf] => ("inspect", pdf),
    ["--markdown", var pdf] => ("markdown", pdf),
    _ => (null, null),
};

if (mode is null || path is null)
{
    Console.Error.WriteLine("Usage: CalyRunner [--inspect|--markdown] <pdf>");
    return 2;
}

var timer = Stopwatch.StartNew();
using var document = PdfDocument.Open(path);
var pages = document.NumberOfPages;
var letterCount = 0;
var markdownChars = 0;

if (mode != "inspect")
{
    document.AddPageFactory<PageTextLayerContent, TextLayerFactory>();
    if (mode == "first-page")
    {
        letterCount = document.GetPage<PageTextLayerContent>(1).Letters.Count;
    }
    else
    {
        var markdown = new StringBuilder();
        for (var pageNumber = 1; pageNumber <= pages; pageNumber++)
        {
            var page = document.GetPage<PageTextLayerContent>(pageNumber);
            var layer = PdfTextLayerHelper.GetTextLayer(page, CancellationToken.None);
            markdown.Append("# Page ").Append(pageNumber).AppendLine();
            foreach (var block in layer.TextBlocks)
            {
                foreach (var line in block.TextLines)
                {
                    markdown.AppendLine(string.Join(' ', line.Words.Select(word => word.Value)));
                }
                markdown.AppendLine();
            }
        }
        markdownChars = markdown.Length;
    }
}
timer.Stop();
Console.WriteLine(JsonSerializer.Serialize(new { elapsed_ms = timer.Elapsed.TotalMilliseconds, mode, pages, letters = letterCount, markdown_chars = markdownChars }));
return 0;
