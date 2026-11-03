// Mapeo entre código numérico ISO 3166-1 (en world-atlas topojson) y código Alpha-3
export const NUMERIC_TO_ALPHA3: Record<string, string> = {
  "004": "AFG", "008": "ALB", "012": "DZA", "024": "AGO", "032": "ARG",
  "036": "AUS", "040": "AUT", "031": "AZE", "050": "BGD", "056": "BEL",
  "068": "BOL", "070": "BIH", "072": "BWA", "076": "BRA", "100": "BGR",
  "116": "KHM", "120": "CMR", "124": "CAN", "140": "CAF", "148": "TCD",
  "152": "CHL", "156": "CHN", "170": "COL", "178": "COG", "180": "COD",
  "188": "CRI", "191": "HRV", "192": "CUB", "196": "CYP", "203": "CZE",
  "208": "DNK", "214": "DOM", "218": "ECU", "818": "EGY", "222": "SLV",
  "231": "ETH", "242": "FJI", "246": "FIN", "250": "FRA", "266": "GAB",
  "268": "GEO", "276": "DEU", "288": "GHA", "300": "GRC", "320": "GTM",
  "324": "GIN", "332": "HTI", "340": "HND", "348": "HUN", "352": "ISL",
  "356": "IND", "360": "IDN", "364": "IRN", "368": "IRQ", "372": "IRL",
  "376": "ISR", "380": "ITA", "388": "JAM", "392": "JPN", "400": "JOR",
  "398": "KAZ", "404": "KEN", "408": "PRK", "410": "KOR", "414": "KWT",
  "418": "LAO", "422": "LBN", "426": "LSO", "430": "LBR", "434": "LBY",
  "440": "LTU", "442": "LUX", "450": "MDG", "454": "MWI", "458": "MYS",
  "466": "MLI", "478": "MRT", "484": "MEX", "496": "MNG", "504": "MAR",
  "508": "MOZ", "516": "NAM", "524": "NPL", "528": "NLD", "554": "NZL",
  "558": "NIC", "562": "NER", "566": "NGA", "578": "NOR", "512": "OMN",
  "586": "PAK", "591": "PAN", "598": "PNG", "600": "PRY", "604": "PER",
  "608": "PHL", "616": "POL", "620": "PRT", "634": "QAT", "642": "ROU",
  "643": "RUS", "646": "RWA", "682": "SAU", "686": "SEN", "688": "SRB",
  "702": "SGP", "703": "SVK", "705": "SVN", "706": "SOM", "710": "ZAF",
  "724": "ESP", "144": "LKA", "729": "SDN", "752": "SWE", "756": "CHE",
  "760": "SYR", "764": "THA", "768": "TGO", "788": "TUN", "792": "TUR",
  "800": "UGA", "804": "UKR", "784": "ARE", "826": "GBR", "840": "USA",
  "858": "URY", "860": "UZB", "862": "VEN", "704": "VNM", "887": "YEM",
  "894": "ZMB", "716": "ZWE",
  "834": "TZA", "732": "ESH", "044": "BHS", "238": "FLK", "304": "GRL", "260": "ATF",
  "626": "TLS", "084": "BLZ", "328": "GUY", "740": "SUR", "630": "PRI", "204": "BEN",
  "384": "CIV", "624": "GNB", "694": "SLE", "854": "BFA", "226": "GNQ", "748": "SWZ",
  "108": "BDI", "275": "PSE", "270": "GMB", "548": "VUT", "104": "MMR", "064": "BTN",
  "762": "TJK", "417": "KGZ", "795": "TKM", "051": "ARM", "112": "BLR", "498": "MDA",
  "428": "LVA", "233": "EST", "540": "NCL", "090": "SLB", "158": "TWN", "096": "BRN",
  "232": "ERI", "010": "ATA", "262": "DJI", "807": "MKD", "499": "MNE", "780": "TTO",
  "728": "SSD",
};

// Respaldo de normalización por nombre común
export const NAME_TO_ALPHA3: Record<string, string> = {
  "united states of america": "USA",
  "united states": "USA",
  "canada": "CAN",
  "mexico": "MEX",
  "brazil": "BRA",
  "argentina": "ARG",
  "chile": "CHL",
  "colombia": "COL",
  "peru": "PER",
  "spain": "ESP",
  "france": "FRA",
  "germany": "DEU",
  "united kingdom": "GBR",
  "italy": "ITA",
  "portugal": "PRT",
  "russia": "RUS",
  "china": "CHN",
  "japan": "JPN",
  "south korea": "KOR",
  "india": "IND",
  "australia": "AUS",
  "new zealand": "NZL",
  "south africa": "ZAF",
  "egypt": "EGY",
  "nigeria": "NGA",
  "norway": "NOR",
  "sweden": "SWE",
  "finland": "FIN",
  "poland": "POL",
  "ukraine": "UKR",
  "saudi arabia": "SAU",
};

export function getAlpha3Code(numericOrStringId: string | number, countryName?: string): string {
  const paddedId = String(numericOrStringId).padStart(3, "0");
  if (NUMERIC_TO_ALPHA3[paddedId]) {
    return NUMERIC_TO_ALPHA3[paddedId];
  }
  if (countryName) {
    const key = countryName.toLowerCase().trim();
    if (NAME_TO_ALPHA3[key]) {
      return NAME_TO_ALPHA3[key];
    }
  }
  return paddedId;
}
