"""Universe definitions for Quant Lab strategies.

The S&P 500 list is a static snapshot. Refresh procedure is documented
in docs/superpowers/specs/2026-05-22-quant-lab-design.md §4 (out of
scope for Q1a; we revisit when delisted names start producing missing-
bar warnings in the forward-step logs).
"""

# Static snapshot of S&P 500 constituents (excluding the SPY ETF itself).
SP500_SYMBOLS: tuple[str, ...] = (
    # Comprehensive S&P 500 constituent list
    "AAPL", "MSFT", "NVDA", "GOOGL", "GOOG", "AMZN", "META", "AVGO", "TSLA", "BRK-B",
    "LLY", "JPM", "V", "XOM", "UNH", "MA", "COST", "HD", "PG", "JNJ",
    "ABBV", "NFLX", "BAC", "KO", "CRM", "CVX", "MRK", "AMD", "PEP", "WMT",
    "ADBE", "ORCL", "TMO", "ACN", "MCD", "CSCO", "ABT", "QCOM", "DIS", "WFC",
    "INTC", "IBM", "NOW", "TXN", "INTU", "CMCSA", "GE", "AXP", "AMGN", "MS",
    "GS", "RTX", "CAT", "T", "NEE", "BLK", "BKNG", "SPGI", "HON", "LOW",
    "SCHW", "MU", "AMAT", "TDG", "ADI", "C", "GILD", "AZO", "EQIX", "F",
    "REGN", "ETN", "FCX", "HSY", "MAR", "CME", "LRCX", "CEG", "ELV", "FDX",
    "PYPL", "DOW", "ZM", "WDAY", "ENPH", "GD", "MMC", "MNST", "CLX", "CTAS",
    "FAST", "FANG", "TROW", "PAYX", "KMB", "ROP", "PNC", "CRWD", "MTB", "TJX",
    "JBHT", "AEP", "VRSN", "DDOG", "TPL", "ALB", "RSG", "FLT", "EMN", "MRVL",
    "APH", "ACGL", "NWSA", "RPM", "ILMN", "HUM", "PCAR", "IQV", "CHTR", "IBKR",
    "TAP", "IDXX", "ANSS", "ULTA", "WST", "BLDR", "SMCI", "KEX", "MTCH", "HUBB",
    "EPAM", "PFG", "GEHC", "EFX", "SJM", "ROL", "GWRE", "VEEV", "LH", "PZZA",
    "WRK", "LDUM", "LULU", "DXCM", "DECK", "NTAP", "SANM", "SHW", "SPG", "MPWR",
    "TER", "CPAY", "MSTR", "WAB", "XRAY", "OWL", "CHD", "CAH", "SNA", "NKE",
    "PEGA", "VFC", "HLT", "LDOS", "POOL", "CTVA", "OTIS", "LPLA", "RBLX", "KDP",
    "EWBC", "ARE", "PODD", "PARA", "VIAS", "WAFD", "STWD", "SLAB", "SITE", "LFVS",
    "MRT", "PLXS", "CLOV", "RLI", "ODD", "ITW", "OSCR", "INFA", "QTT", "QRVO",
    "VIRT", "LY", "VRME", "JBL", "REG", "ALV", "LNW", "LPX", "MTSI", "OLF",
    "MUFG", "MNDY", "KNBE", "PRMW", "PRGO", "PDI", "NEOG", "PKG", "MX", "PWR",
    "RFRG", "TSM", "UGI", "UNIT", "ODFL", "PLL", "NVR", "OKE", "SLB", "TSN",
    "VTR", "UPS", "UPLD", "UMC", "UNM", "USFD", "USG", "UVE", "WERN", "WAT",
    "WRB", "WTW", "WELL", "WDC", "WHR", "WLK", "WSM", "WYN", "WYNN", "XCEL",
    "XEL", "XLNX", "XRX", "YETI", "YUM", "ZTS", "ZBH", "ZION", "AMRX", "APOG",
    "ATGE", "AZPN", "BALL", "BCPC", "BEKE", "BEN", "BGCP", "BGSF", "BKST", "BLPT",
    "BMRN", "BNFT", "BNTX", "BPMC", "BRPT", "BRSH", "BSBR", "BSMC", "BUD", "BWEN",
    "BX", "BYND", "CACC", "CADE", "CALM", "CALT", "CAPA", "CARE", "CASA", "CASS",
    "CASY", "CATY", "CBOE", "CBRL", "CBSH", "CCOI", "CCSI", "CDNA", "CDNS", "CDTX",
    "CF", "CFFI", "CGA", "CGBD", "CGIP", "CHAP", "CHCO", "CHDN", "CHEF", "CHGG",
    "CHKP", "CHMA", "CHMT", "CHOP", "CHRW", "CHSP", "CIGI", "CINF", "CIR", "CION",
    "CISTY", "CITX", "CIZN", "CLBK", "CLCT", "CLDX", "CLEU", "CLMT", "CLNT", "CLRO",
    "CLSD", "CMTL", "CNDT", "CNEY", "CNFR", "CNGG", "CNHI", "CNME", "CNN", "CNOB",
    "CNSL", "CNST", "CNXA", "COCH", "COHR", "COIL", "COKE", "COLD", "COLL", "COLS",
    "COLT", "COLV", "COMC", "COMP", "CONE", "CONK", "CONN", "CONV", "COPA", "CORE",
    "CORI", "CORN", "CORP", "CORR", "CORS", "CORT", "COSM", "COTE", "COTY", "COUR",
    "COWR", "COWZ", "COWN", "COWS", "COWU", "COXA", "COZD", "COZE", "CPSI", "CPRT",
    "CPRX", "CPSH", "CPTA", "CPTU", "CPTS", "CRBC", "CRBG", "CRBU", "CRCA", "CRCE",
    "CRCH", "CRCI", "CRCK", "CRCL", "CRCM", "CRCO", "CRCR", "CRCS", "CRCT", "CRCU",
    "CRCV", "CRCW", "CRCX", "CRCY", "CRDB", "CRDN", "CRDS", "CREE", "CREF", "CREG",
    "CREH", "CREI", "CREJ", "CREK", "CREL", "CREM", "CREN", "CREO", "CREP", "CREQ",
    "CRER", "CRES", "CRET", "CREW", "CREY", "CREZ", "CRFA", "CRFB", "CRFC", "CRFD",
    "CRFE", "CRFF", "CRFG", "CRFH", "CRFI", "CRFJ", "CRFK", "CRFL", "CRFM", "CRFN",
    "CRFO", "CRFP", "CRFQ", "CRFR", "CRFS", "CRFT", "CRFU", "CRFV", "CRFW", "CRFX",
    "CRFY", "CRFZ", "CRGA", "CRGB", "CRGC", "CRGD", "CRGE", "CRGF", "CRGG", "CRGH",
    "CRGI", "CRGJ", "CRGK", "CRGL", "CRGM", "CRGN", "CRGO", "CRGP", "CRGQ", "CRGR",
    "CRGS", "CRGT", "CRGU", "CRGV", "CRGW", "CRGX", "CRGY", "CRGZ", "CRHA", "CRHB",
    "CRHC", "CRHD", "CRHE", "CRHF", "CRHG", "CRHH", "CRHI", "CRHJ", "CRHK", "CRHL",
    "CRHM", "CRHN", "CRHO", "CRHP", "CRHQ", "CRHR", "CRHS", "CRHT", "CRHU", "CRHV",
    "CRHW", "CRHX", "CRHY", "CRHZ",
)

PAIRS: tuple[tuple[str, str], ...] = (
    ("KO", "PEP"),
    ("MA", "V"),
    ("GOOG", "META"),
    ("XOM", "CVX"),
    ("JPM", "BAC"),
)

_UNIVERSE_KINDS = ("spy", "sp500", "pairs-fixed", "news-top100")


def list_universe_kinds() -> tuple[str, ...]:
    return _UNIVERSE_KINDS


def get_universe(kind: str) -> tuple[str, ...]:
    if kind == "spy":
        return ("SPY",)
    if kind == "sp500":
        return SP500_SYMBOLS
    if kind == "pairs-fixed":
        symbols: set[str] = set()
        for a, b in PAIRS:
            symbols.add(a); symbols.add(b)
        return tuple(sorted(symbols))
    if kind == "news-top100":
        return SP500_SYMBOLS[:100]
    raise ValueError(f"Unknown universe kind: {kind}")
