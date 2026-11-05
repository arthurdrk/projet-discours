import spacy

nlp = None


def get_nlp():
    global nlp
    if nlp is None:
        nlp = spacy.load("en_core_web_sm")
    return nlp


def place_extract(text):
    treated_text = nlp(text)
    places = []
    for entity in treated_text.ents:
        if entity.label_ == "GPE" and entity.text not in places:
            places.append(entity.text)
    return places
