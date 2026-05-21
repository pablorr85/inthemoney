import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY", "TU_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "TU_API_SECRET")
MAX_BUDGET_PER_TRADE = float(os.getenv("MAX_BUDGET_PER_TRADE", 5000))

MARKETS = {
    "US": {
        "name": "Wall Street (NYSE/NASDAQ)",
        "open_hour": 15,
        "open_minute": 30,
        "close_hour": 22,
        "close_minute": 0,
        "tickers": [
            "MSFT", "AAPL", "NVDA", "ASML", "TSM", "AVGO", "AMD", "INTC",
            "META", "GOOGL", "AMZN", "NFLX", "CRM", "ADBE", "INTU",
            "CRWD", "PANW", "FTNT", "PLTR", "DDOG", "SNOW",
            "LMT", "RTX", "NOC", "GD", "BA", "CAT", "DE", "HON", "GE", "ETN",
            "LLY", "NVO", "UNH", "JNJ", "ABBV", "MRK", "TMO", "DHR",
            "COST", "WMT", "PG", "KO", "PEP", "MCD", "SBUX", "MDLZ", "K", "GIS", "HSY", "KHC", "TSN", "BYND", "DPZ", "YUM", "CMG",
            "V", "MA", "AXP", "JPM", "BAC", "MS", "GS",
            "XOM", "CVX", "COP", "OXY", "NEE", "GEV", "ENPH", "FSLR",
            "CCJ", "CEG", "BWXT", "SMR", "NXE", "OKLO",
            "GLD", "NEM", "GOLD", "FCX"
        ]
    },
    "ES": {
        "name": "Bolsa Española (BME)",
        "open_hour": 9,
        "open_minute": 0,
        "close_hour": 17,
        "close_minute": 30,
        "tickers": [
            "AMS.MC", "IDR.MC", "TEF.MC", "CLNX.MC",
            "ACS.MC", "AENA.MC", "FER.MC", "IAG.MC", "AIR.MC", "ANA.MC", "SCYR.MC",
            "FCC.MC", "OHLA.MC", "SJO.MC", "MVC.MC", "AEDAS.MC", "HOME.MC", "CMO.MC",
            "ENO.MC", "EZE.MC", "MDF.MC", "TRE.MC", "AMP.MC",
            "ROVI.MC", "PHM.MC", "GRF.MC",
            "ITX.MC", "VIS.MC", "PUIG.MC", "EBRO.MC", "DIA.MC",
            "SAN.MC", "BBVA.MC", "CABK.MC", "SAB.MC", "BKT.MC", "UNI.MC", "MAP.MC",
            "IBE.MC", "REP.MC", "ELE.MC", "NTGY.MC", "ENG.MC", "RED.MC", "ANE.MC", "SLR.MC",
            "COL.MC", "MRL.MC",
            "ACX.MC", "MTS.MC", "FDR.MC", "LOG.MC"
        ]
    },
    "FR": {
        "name": "Bolsa de París (Euronext)",
        "open_hour": 9,
        "open_minute": 0,
        "close_hour": 17,
        "close_minute": 30,
        "tickers": [
            "SAF.PA", "MC.PA", "TTE.PA", "SAN.PA", "SU.PA", "RMS.PA", "DSY.PA", "AI.PA",
            "OR.PA", "BNP.PA", "DG.PA", "EL.PA", "CS.PA", "BN.PA", "RI.PA", "KER.PA", "CAP.PA", "STMPA.PA"
        ]
    },
    "DE": {
        "name": "Bolsa de Fráncfort (Xetra)",
        "open_hour": 9,
        "open_minute": 0,
        "close_hour": 17,
        "close_minute": 30,
        "tickers": [
            "SAP.DE", "SIE.DE", "ALV.DE", "RHM.DE", "IFX.DE", "MBG.DE", "BMW.DE", "VOW3.DE",
            "DTE.DE", "MUV2.DE", "DHL.DE", "BAS.DE", "BAYN.DE", "ADS.DE", "DBK.DE", "EOAN.DE", "RWE.DE", "ENR.DE"
        ]
    }
}
