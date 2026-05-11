from importlib import resources

from d3textdb import D3TextDB

db_path = resources.files("ahbackend.db") / "database.db"
annodb = D3TextDB(db_path, echo=False)
