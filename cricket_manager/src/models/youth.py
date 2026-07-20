"""League-country youth routing."""
COUNTRY_NAMES={"england":"England","australia":"Australia","india":"India","pakistan":"Pakistan",
"south_africa":"South Africa","new_zealand":"New Zealand","west_indies":"West Indies",
"bangladesh":"Bangladesh","sri_lanka":"Sri Lanka","afghanistan":"Afghanistan"}
def nationality_for_country_id(country_id:str)->str:return COUNTRY_NAMES.get(country_id,"England")
