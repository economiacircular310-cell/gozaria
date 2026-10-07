"""Textos que se usan en varias páginas: puntos fuertes, preguntas frecuentes y fotos."""
from __future__ import annotations

PUNTOS_FUERTES = {
    "es": [
        ("cafe", "Café de especialidad", "Espresso, café de filtro y bebidas de autor, preparados con calma."),
        ("brunch", "Brunch todo el día", "Tostadas de masa madre, huevos poché, bowls y smash burgers a cualquier hora."),
        ("reposteria", "Repostería artesana", "Cookies, tartas, bizcochos y bollería para acompañar el café."),
        ("sala", "Sala para eventos y talleres", "Una sala anexa para celebraciones, reuniones, cenas y clases, con catering propio."),
        ("perro", "Pet friendly", "Tu perro es bienvenido dentro del local."),
        ("espiga", "Opciones sin gluten", "Tenemos productos elaborados sin gluten. Pregúntanos en barra."),
    ],
    "en": [
        ("cafe", "Specialty coffee", "Espresso, filter coffee and signature drinks, made with care."),
        ("brunch", "All-day brunch", "Sourdough toasts, poached eggs, bowls and smash burgers at any time."),
        ("reposteria", "Homemade pastries", "Cookies, cakes, sponge cakes and pastries to go with your coffee."),
        ("sala", "Room for events and workshops", "A separate room for celebrations, meetings, dinners and classes, with our own catering."),
        ("perro", "Dog friendly", "Your dog is welcome inside."),
        ("espiga", "Gluten-free options", "We have gluten-free products. Ask us at the counter."),
    ],
}

FAQ = {
    "es": [
        ("¿Tenéis opciones sin gluten?",
         "Sí. Tenemos productos elaborados sin gluten; pregúntanos en barra qué hay ese día."),
        ("¿Puedo ir con mi perro?",
         "Sí. Gosaria es pet friendly: tu perro puede entrar contigo al local."),
        ("¿Hay que reservar mesa?",
         "No. Funcionamos por orden de llegada, también con grupos. Si sois muchos, os recomendamos llegar pronto."),
        ("¿Se puede alquilar la sala?",
         "Sí. Tenemos una sala anexa para celebraciones, reuniones, cenas y talleres, desde 25 € la hora y con catering propio."),
    ],
    "en": [
        ("Do you have gluten-free options?",
         "Yes. We have gluten-free products; ask at the counter what is available that day."),
        ("Can I bring my dog?",
         "Yes. Gosaria is dog friendly: your dog can come inside with you."),
        ("Do I need to book a table?",
         "No. We work on a first-come, first-served basis, groups included. If you are a large group, we recommend arriving early."),
        ("Can I hire the room?",
         "Yes. We have a separate room for celebrations, meetings, dinners and workshops, from €25 an hour and with our own catering."),
    ],
}

# Texto alternativo de cada foto (ver scripts/build_assets.py)
FOTOS_ALT = {
    "desayuno": ("Desayuno visto desde arriba: tostada de aguacate, café con leche con dibujo, zumo de naranja y bowl de yogur con fruta",
                 "Breakfast from above: avocado toast, latte art, orange juice and a yogurt bowl with fruit"),
    "barra": ("Barra de Gosaria con la vitrina de repostería iluminada",
              "Gosaria's counter with the lit pastry display case"),
    "sala": ("Sala multiusos con mesas amarillas y grandes ventanales",
             "Multi-purpose room with yellow tables and large windows"),
    "mesa-alta": ("Mesa alta amarilla con taburetes junto a los ventanales",
                  "Tall yellow table with stools by the windows"),
    "catering-bowls": ("Mesa de catering con bowls de yogur, bizcocho y bollería",
                       "Catering spread with yogurt bowls, sponge cake and pastries"),
    "catering-tostas": ("Bandeja de tostas de jamón ibérico en un catering",
                        "Tray of Iberian ham toasts at a catering event"),
    "fruta": ("Plato de fresas, kiwi y naranja alrededor de un cuenco de chocolate",
              "Platter of strawberries, kiwi and orange around a bowl of chocolate"),
    "taller": ("Taller en la sala de Gosaria, con el público sentado en las mesas amarillas",
               "A workshop in Gosaria's room, with the audience at the yellow tables"),
    "local-lleno": ("Salón de Gosaria lleno de gente una tarde",
                    "Gosaria's main room full of people one afternoon"),
    "bebidas": ("Tres bebidas frías sobre una mesa de madera junto a una planta",
                "Three cold drinks on a wooden table next to a plant"),
    "acai": ("Bowl de açaí con plátano, fresas, granola y coco rallado",
             "Açaí bowl with banana, strawberries, granola and grated coconut"),
    "rincon": ("Rincón con sofá, mesa baja y estanterías con productos",
               "Corner with a sofa, a coffee table and shelves of products"),
    "salon": ("Salón principal con mesas de madera y luz natural",
              "Main room with wooden tables and natural light"),
}


def alt(nombre: str, lang: str) -> str:
    es, en = FOTOS_ALT[nombre]
    return es if lang == "es" else en
