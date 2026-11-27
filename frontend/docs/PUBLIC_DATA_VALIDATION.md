# Public manufacturing data validation

Use the checks below to verify Gantt layout and browser interactions with published manufacturing records. They use local files and run without an application database.

## Sources and coverage

- Gabriel Azevedo David, Kaiser Werlly Miranda Monson, and Celso de Araujo Soares Junior published a bottling-line downtime log. The check uses all 1,388 records across 55 days. It converts the recorded Excel wall-clock fractions to hours within each recorded day and checks the recorded duration. [Zenodo record](https://zenodo.org/records/18146866)
- Frank Engelmann and Robert H. Schmitt published CNC machine telemetry from series production. The November 26, 2021 file contains 12,388 readings. The check derives 124 observed spans by joining adjacent readings with the same phase and a positive gap of at most five seconds. It skips 225 adjacent pairs at phase changes, duplicate timestamps, or longer gaps. [Zenodo record](https://zenodo.org/records/10853254)
- Duygu Yilmaz Eroglu published a textile scheduling instance with 100 orders, 5 families, 10 machines, and 25 family changeover entries. The check verifies unique IDs and family references. The file has no realized machine assignments or operation timestamps. [Zenodo record](https://zenodo.org/records/15487235)

The shared layout passed on 1,512 time intervals across 56 rows. One row contained overlapping events. The check verified bar coordinates against record timestamps, separation of overlapping events, and lane count against independently measured peak concurrency.

## Run in PowerShell

From the repository's `frontend` directory, use Python 3.10 or later and Node 24. The files stay in `$env:TEMP`.

```powershell
$dataPath = Join-Path $env:TEMP 'IndoFlow-public-data'
New-Item -ItemType Directory -Force -Path $dataPath | Out-Null
curl.exe --fail --location --output (Join-Path $dataPath 'production_raw.xlsx') 'https://zenodo.org/records/18146866/files/production_raw.xlsx?download=1'
curl.exe --fail --location --output (Join-Path $dataPath 'Data_from_2021-11-26.csv') 'https://zenodo.org/records/10853254/files/Data_from_2021-11-26.csv?download=1'
curl.exe --fail --location --output (Join-Path $dataPath 'textile-dataset.rar') 'https://zenodo.org/records/15487235/files/Dataset.rar?download=1'
tar.exe -xf (Join-Path $dataPath 'textile-dataset.rar') -C $dataPath Dataset/Data_i100_f5_k10
python scripts/public_data_records.py $dataPath
node scripts/validate-public-timeline.mjs (Join-Path $dataPath 'observed-timeline.json')
```

## Browser measurement

With frontend dependencies, Python Playwright and Microsoft Edge installed, run from the `frontend` directory after the layout check:

```powershell
python scripts/measure-public-gantt.py (Join-Path $dataPath 'observed-timeline.json')
```

The runner builds the app's Gantt component and styles in a local test page. Source groups supply the row labels, and record IDs identify the intervals. The source records do not carry order due dates. The browser checks that the bars announce “Status unavailable” and that both status filters exclude them. It reaches the last page, confirms that each page renders at most 100 bars, and checks zoom, resource filtering and filter reset at each viewport.

The table shows the median and maximum in milliseconds from five runs per viewport in headless Edge 158 on this Windows PC. Initial render starts immediately before React mount and ends two animation frames after the bars enter the page. Interactions are measured from the browser event through two animation frames. Each resulting state is verified separately. These measurements cover the component with local records and exclude download, API and solver time.

| Viewport | Initial render | Next page | Zoom | Resource filter | Clear filters |
| --- | ---: | ---: | ---: | ---: | ---: |
| Desktop 1440 × 900 | 30.7 / 215.3 | 10.6 / 13.2 | 6.6 / 7.8 | 9.4 / 21.0 | 10.2 / 10.7 |
| Laptop 1280 × 800 | 28.1 / 66.8 | 10.4 / 12.8 | 7.1 / 7.7 | 9.4 / 9.7 | 9.8 / 10.5 |
| Tablet 768 × 1024 | 29.7 / 67.1 | 10.5 / 12.5 | 6.6 / 7.6 | 9.3 / 9.7 | 9.8 / 10.2 |
| Phone 390 × 844 | 31.9 / 67.1 | 10.5 / 13.7 | 6.2 / 6.4 | 9.3 / 9.9 | 9.7 / 10.2 |

## Verify an approved historical snapshot

The populated API browser flow requires metal injection molding work orders, due dates, machine capabilities, routes and calendars under the backend contract. A published visit to INDO-MIM's San Antonio plant describes how it links batch IDs to machines and orders, but provides no downloadable work orders, timestamps or calendars. [PIM International plant report](https://www.pim-international.com/articles/indo-mim-in-north-america-scaling-mim-and-developing-binder-jetting-to-meet-evolving-market-needs/)

Ask the backend owner for a permission-cleared SQLite snapshot and the ID of an active resource with a feasible outage scenario. See [Backend requests](BACKEND_REQUESTS.md#permission-cleared-historical-mim-snapshot).

From the repository root, set `$approvedSnapshot` to the absolute path of the supplied SQLite file and `$outageResourceId` to the supplied resource ID. With the local Python environment, Playwright, Edge and frontend dependencies installed, run:

```powershell
python frontend/scripts/browser_real_api.py --historical-db $approvedSnapshot --outage-resource-id $outageResourceId
```

The script opens the snapshot read-only, copies it to a temporary directory and starts the API on that copy. The API saves the comparison there. The script checks the comparison and Gantt keyboard navigation. It verifies that both the outage and reset runs return schedules and echo the submitted inputs, that no outage operation is assigned to the unavailable resource, and that the reset result shows the cleared inputs. Screenshots are off by default. If the data owner approves captures, use `--screenshots` with a private folder outside both the frontend and backend checkouts. The runner rejects capture paths inside either checkout.

Add `--axe-script $axeScript` with the absolute path to a local `axe.min.js` to scan the populated flow board, selected operation details, optimizer timeline, outage scenario and scenario after resetting inputs. The scan reports rule IDs and counts for violations and manual review. Follow up with the [manual screen-reader check](FRONTEND_AUDIT.md#manual-screen-reader-check).
