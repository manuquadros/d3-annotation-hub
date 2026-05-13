def cse_citation(authors: str, year: int) -> str:
    """Build a CSE-style citation key from semicolon-separated authors and year.

    Authors are expected in "LastName, GivenName" format separated by "; ".
    """
    parts = [a.strip() for a in authors.split(";") if a.strip()]
    last_names = [p.split(",")[0].strip() for p in parts]
    if not last_names:
        return str(year)
    if len(last_names) == 1:
        return f"{last_names[0]} {year}"
    if len(last_names) == 2:
        return f"{last_names[0]} & {last_names[1]} {year}"
    return f"{last_names[0]} et al. {year}"
