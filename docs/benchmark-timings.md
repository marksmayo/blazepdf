# Full benchmark timing tables

All values are median milliseconds. Compare only within each document/workload row. A dash means no successful measurement, not zero. BlazePDF: nine samples on 2 October 2026. Competitors: retained 30 September rows with five or six samples. This is not a simultaneous rerun.

Source: [benchmark-20261002T072651Z-merged.json](../results/benchmark-20261002T072651Z-merged.json).

## classify + extract markdown

| Document | BlazePDF | CalyPdf | MuPDF | pdf-inspector |
| --- | ---: | ---: | ---: | ---: |
| Financial table | 22.112 | 574.465 | 28.259 | 53.908 |
| Image document | 270.299 | 7554.687 | 298.699 | 1977.717 |
| Multi-column | 26.242 | 699.113 | 76.499 | 69.790 |
| Overlapping text | 18.367 | 1508.033 | 80.300 | — |
| RTL Hebrew | 16.577 | 1190.142 | 35.085 | 34.018 |
| Rotation | 16.893 | 946.069 | 35.139 | 41.247 |
| Signed PDF | 20.909 | 690.752 | 46.613 | 50.525 |
| Text-heavy | 31.393 | 1568.262 | 38.074 | 152.845 |

## classify only

| Document | BlazePDF | CalyPdf | MuPDF | PDF24 bundled qpdf | SumatraPDF | pdf-inspector |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Financial table | 12.381 | 408.810 | 67.002 | 31.924 | 70.457 | 22.855 |
| Image document | 21.419 | 490.789 | 23.506 | 30.298 | 37.172 | 233.477 |
| Multi-column | 14.033 | 480.098 | 20.671 | 48.941 | 27.006 | 41.622 |
| Overlapping text | 18.301 | 493.923 | 24.308 | 62.170 | 28.689 | 45.124 |
| RTL Hebrew | 14.543 | 504.969 | 39.309 | 82.156 | 37.903 | 27.489 |
| Rotation | 13.050 | 550.429 | 21.672 | 49.743 | 30.253 | 41.212 |
| Signed PDF | 16.811 | 479.285 | 29.015 | 39.281 | 32.721 | 42.032 |
| Text-heavy | 13.455 | 385.911 | 14.389 | 86.980 | 75.487 | 22.725 |

## launch to visible document window

| Document | BlazePDF | Foxit PDF Reader | Google Chrome PDF viewer | MuPDF | Okular | PDF24 Reader | Sejda PDF Desktop | SumatraPDF | Xodo PDF Reader |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Financial table | 20.593 | 1113.150 | 630.698 | 115.028 | 550.001 | 196.583 | 1790.094 | 2380.867 | 10443.569 |
| Image document | 20.455 | 988.064 | 812.206 | 2252.085 | — | 372.615 | 941.345 | 760.565 | 8575.720 |
| Multi-column | 20.254 | 1029.823 | 664.982 | 90.327 | 843.259 | 199.126 | 1758.252 | 1825.745 | 9860.207 |
| Overlapping text | 20.287 | 569.431 | 550.425 | 128.300 | — | 289.665 | 1268.434 | 1772.835 | 12811.831 |
| RTL Hebrew | 21.606 | 648.994 | 796.004 | 44.140 | 500.549 | 254.619 | 1073.620 | 1809.204 | 12906.222 |
| Rotation | 20.355 | 1122.601 | 561.141 | 72.137 | 738.341 | 310.766 | 1595.862 | 2912.572 | 11051.327 |
| Signed PDF | 20.033 | 2452.028 | 426.603 | 72.812 | 840.614 | 373.708 | 1310.137 | 2992.233 | 17461.314 |
| Text-heavy | 19.940 | 774.714 | 716.040 | 67.089 | 661.726 | 242.020 | 1211.485 | 345.338 | 8473.150 |

## open document + first-page text layer

| Document | BlazePDF | CalyPdf | MuPDF | SumatraPDF | pdf-inspector |
| --- | ---: | ---: | ---: | ---: | ---: |
| Financial table | 16.066 | 509.219 | 52.871 | 49.367 | 40.013 |
| Image document | 190.402 | 1004.343 | 369.116 | 259.716 | 557.056 |
| Multi-column | 16.149 | 2137.365 | 45.057 | 59.491 | 23.606 |
| Overlapping text | 19.844 | 908.765 | 49.703 | 115.478 | 47.337 |
| RTL Hebrew | 13.055 | 981.321 | 25.190 | 59.385 | 50.883 |
| Rotation | 12.890 | 680.401 | 65.833 | 48.159 | 39.541 |
| Signed PDF | 17.627 | 712.550 | 39.021 | 57.824 | 46.822 |
| Text-heavy | 24.715 | 814.039 | 56.882 | 73.433 | 92.055 |

## render first page at 150 DPI

| Document | BlazePDF | MuPDF |
| --- | ---: | ---: |
| Financial table | 43.791 | 107.538 |
| Image document | 634.231 | 2504.587 |
| Multi-column | 32.257 | 143.759 |
| Overlapping text | 126.200 | 300.778 |
| RTL Hebrew | 30.395 | 72.218 |
| Rotation | 35.906 | 154.254 |
| Signed PDF | 35.599 | 131.809 |
| Text-heavy | 46.059 | 143.413 |
