#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Génère un fichier ArchiMate natif (.archimate) compatible avec Archi,
via la fonction gen_schema(app, sources, targets).

Format de chaque application (app / sources / targets) :
    {"title": "MonApp", "label": "Application centrale"}

  - `title`  -> nom de l'ApplicationComponent (1ère ligne affichée, en gras)
  - `label`  -> sous-texte affiché en 2ème ligne dans la boîte

Règles métier :
  - sources  : liste de dicts {"title":..., "label":...} -> flux vers `app`
  - targets  : liste de dicts {"title":..., "label":...} -> flux depuis `app`
  - app      : dict {"title":..., "label":...} -> application centrale
  - Tous les flux (FlowRelationship + connexions graphiques) portent le
    label "<<Costream>>".
  - Les boîtes "sources" et "targets" partagent TOUTES la même taille
    (largeur ET hauteur), calculée pour que le texte le plus long
    (titre ou label, sur l'ensemble des sources + targets) rentre
    correctement. Si une seule boîte a besoin de plus de place, TOUTES
    s'agrandissent en conséquence.
  - La boîte `app` (centrale) a sa PROPRE taille, calculée uniquement
    à partir de son propre texte (titre + label), indépendamment des
    sources/targets.

Dépendances : uniquement la bibliothèque standard (xml.etree.ElementTree,
uuid).
"""

import uuid
import xml.etree.ElementTree as ET


# ----------------------------------------------------------------------
# Constantes de mise en forme du texte (approximation de rendu)
# ----------------------------------------------------------------------

TITLE_CHAR_WIDTH = 7.4     # largeur moyenne d'un caractère du titre (gras, ~12pt)
LABEL_CHAR_WIDTH = 6.2     # largeur moyenne d'un caractère du label (normal, ~10pt)

TITLE_LINE_HEIGHT = 24
LABEL_LINE_HEIGHT = 18

H_PADDING = 40             # marge horizontale totale (gauche + droite) dans la boîte
V_PADDING = 22             # marge verticale totale (haut + bas) dans la boîte

MIN_BOX_WIDTH = 140
MIN_BOX_HEIGHT = 50

COLUMN_MARGIN = 30         # marge verticale ajoutée entre deux boîtes empilées

LEFT_X = 120
GAP = 220                  # longueur des flèches Source<->App et App<->Cible
CONNECTION_LABEL = "<<Costream>>"

NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"
NS_ARCHIMATE = "http://www.archimatetool.com/archimate"


# ----------------------------------------------------------------------
# Utilitaires
# ----------------------------------------------------------------------

def new_id():
    """Génère un identifiant unique au format attendu par Archi."""
    return "id-" + uuid.uuid4().hex


def measure_box(title, label):
    """
    Calcule la largeur/hauteur "naturelle" nécessaire pour afficher
    `title` (ligne 1, gras) et `label` (ligne 2, normal) sans
    troncature, avec un minimum raisonnable.
    """
    title = title or ""
    label = label or ""

    title_w = len(title) * TITLE_CHAR_WIDTH
    label_w = len(label) * LABEL_CHAR_WIDTH
    width = max(title_w, label_w) + H_PADDING

    nb_lines = 2 if (title and label) else 1
    if nb_lines == 2:
        height = TITLE_LINE_HEIGHT + LABEL_LINE_HEIGHT + V_PADDING
    else:
        height = TITLE_LINE_HEIGHT + V_PADDING

    width = max(width, MIN_BOX_WIDTH)
    height = max(height, MIN_BOX_HEIGHT)
    return width, height


def label_expression(item):
    """Construit le texte affiché dans la boîte : titre + label en 2 lignes."""
    title = item.get("title", "") or ""
    label = item.get("label", "") or ""
    if title and label:
        return f"{title}\n{label}"
    return title or label


def _compute_layout(app, sources, targets):
    """
    Calcule toute la géométrie du diagramme (tailles + positions) à
    partir de app/sources/targets. Partagé entre gen_schema() (export
    .archimate) et gen_schema_image() (export image), pour garantir
    que les deux rendus sont rigoureusement identiques.

    Retourne un dict avec :
      side_box_width, side_box_height,
      app_width, app_height, app_x, app_y,
      left_x, left_ys, right_x, right_ys
    """
    all_side_items = list(sources) + list(targets)
    side_widths = []
    side_heights = []
    for item in all_side_items:
        w, h = measure_box(item.get("title", ""), item.get("label", ""))
        side_widths.append(w)
        side_heights.append(h)

    side_box_width = max(side_widths) if side_widths else MIN_BOX_WIDTH
    side_box_height = max(side_heights) if side_heights else MIN_BOX_HEIGHT

    app_width, app_height = measure_box(app.get("title", ""), app.get("label", ""))

    n_left = len(sources)
    n_right = len(targets)
    step_y = side_box_height + COLUMN_MARGIN

    left_total_span = (n_left - 1) * step_y if n_left > 0 else 0
    right_total_span = (n_right - 1) * step_y if n_right > 0 else 0

    y_top = 80
    left_ys = [y_top + i * step_y for i in range(n_left)]

    right_y_start = y_top + (left_total_span - right_total_span) / 2
    right_ys = [round(right_y_start + i * step_y) for i in range(n_right)]

    span_top = min(y_top, right_y_start)
    span_bottom = max(
        y_top + left_total_span + side_box_height,
        right_y_start + right_total_span + side_box_height,
    )
    span_height = span_bottom - span_top

    app_height = max(app_height, span_height)
    center_of_span = (span_top + span_bottom) / 2
    app_y = round(center_of_span - app_height / 2)

    left_x = LEFT_X
    app_x = left_x + side_box_width + GAP
    right_x = app_x + app_width + GAP

    return {
        "side_box_width": side_box_width,
        "side_box_height": side_box_height,
        "app_width": app_width,
        "app_height": app_height,
        "app_x": app_x,
        "app_y": app_y,
        "left_x": left_x,
        "left_ys": left_ys,
        "right_x": right_x,
        "right_ys": right_ys,
    }


# ----------------------------------------------------------------------
# Fonction principale
# ----------------------------------------------------------------------

def gen_schema(app, sources, targets, output_path="flux_mon_app.archimate"):
    """
    Génère le fichier .archimate à partir de :
      - app     : dict {"title": str, "label": str}            -> application centrale
      - sources : liste de dicts {"title": str, "label": str}  -> flux vers `app`
      - targets : liste de dicts {"title": str, "label": str}  -> flux depuis `app`

    Retourne le chemin du fichier généré.
    """

    # ------------------------------------------------------------------
    # 1. Calcul des tailles de boîtes et des positions (layout partagé)
    # ------------------------------------------------------------------

    layout = _compute_layout(app, sources, targets)
    side_box_width = layout["side_box_width"]
    side_box_height = layout["side_box_height"]
    app_width = layout["app_width"]
    app_height = layout["app_height"]
    app_x = layout["app_x"]
    app_y = layout["app_y"]
    left_x = layout["left_x"]
    left_ys = layout["left_ys"]
    right_x = layout["right_x"]
    right_ys = layout["right_ys"]

    # ------------------------------------------------------------------
    # 2. Construction du modèle XML
    # ------------------------------------------------------------------

    model = ET.Element("archimate:model")
    model.set("xmlns:xsi", NS_XSI)
    model.set("xmlns:archimate", NS_ARCHIMATE)
    model.set("name", "Flux " + (app.get("title") or "App"))
    model.set("id", new_id())
    model.set("version", "5.0.0")

    ET.SubElement(model, "folder", {"name": "Strategy", "id": new_id(), "type": "strategy"})
    ET.SubElement(model, "folder", {"name": "Business", "id": new_id(), "type": "business"})
    folder_app = ET.SubElement(model, "folder", {"name": "Application", "id": new_id(), "type": "application"})
    ET.SubElement(model, "folder", {"name": "Technology & Physical", "id": new_id(), "type": "technology"})
    ET.SubElement(model, "folder", {"name": "Motivation", "id": new_id(), "type": "motivation"})
    ET.SubElement(model, "folder", {"name": "Implementation & Migration", "id": new_id(), "type": "implementation_migration"})
    ET.SubElement(model, "folder", {"name": "Other", "id": new_id(), "type": "other"})

    def add_app_component(folder, comp_id, title):
        ET.SubElement(folder, "element", {
            "xsi:type": "archimate:ApplicationComponent",
            "id": comp_id,
            "name": title or "",
        })

    app_id = new_id()
    add_app_component(folder_app, app_id, app.get("title", ""))

    source_ids = []
    for item in sources:
        cid = new_id()
        source_ids.append(cid)
        add_app_component(folder_app, cid, item.get("title", ""))

    target_ids = []
    for item in targets:
        cid = new_id()
        target_ids.append(cid)
        add_app_component(folder_app, cid, item.get("title", ""))

    # --- Relations (FlowRelationship), nom + label "<<Costream>>" ------
    folder_rel = ET.SubElement(model, "folder", {"name": "Relations", "id": new_id(), "type": "relations"})

    def add_flow(folder, src_id, tgt_id, src_title, tgt_title):
        rel_id = new_id()
        ET.SubElement(folder, "element", {
            "xsi:type": "archimate:FlowRelationship",
            "id": rel_id,
            "name": CONNECTION_LABEL,
            "source": src_id,
            "target": tgt_id,
        })
        return rel_id

    source_rel_ids = [
        add_flow(folder_rel, cid, app_id, item.get("title", ""), app.get("title", ""))
        for cid, item in zip(source_ids, sources)
    ]
    target_rel_ids = [
        add_flow(folder_rel, app_id, cid, app.get("title", ""), item.get("title", ""))
        for cid, item in zip(target_ids, targets)
    ]

    # --- Vue (ArchimateDiagramModel) -----------------------------------
    folder_views = ET.SubElement(model, "folder", {"name": "Views", "id": new_id(), "type": "diagrams"})
    view = ET.SubElement(folder_views, "element", {
        "xsi:type": "archimate:ArchimateDiagramModel",
        "name": "Vue Flux " + (app.get("title") or "App"),
        "id": new_id(),
    })

    # ------------------------------------------------------------------
    # 3. Création des objets graphiques (<child>)
    # ------------------------------------------------------------------

    graphical_id_of = {}
    diagram_obj_of = {}

    def add_diagram_object(parent, element_id, x, y, w, h, text, font_bold=False):
        diag_id = new_id()
        graphical_id_of[element_id] = diag_id
        attrs = {
            "xsi:type": "archimate:DiagramObject",
            "id": diag_id,
            "archimateElement": element_id,
        }
        if font_bold:
            attrs["font"] = "1|Lucida Grande|12.0|1|COCOA|1|LucidaGrande-Bold"
            attrs["textPosition"] = "1"
        obj = ET.SubElement(parent, "child", attrs)
        ET.SubElement(obj, "bounds", {
            "x": str(round(x)), "y": str(round(y)),
            "width": str(round(w)), "height": str(round(h)),
        })
        ET.SubElement(obj, "feature", {"name": "labelExpression", "value": text})
        diagram_obj_of[element_id] = obj
        return diag_id

    # App au centre, taille personnalisée
    add_diagram_object(
        view, app_id,
        x=app_x, y=app_y, w=app_width, h=app_height,
        text=label_expression(app), font_bold=True,
    )

    # Sources à gauche, taille uniforme
    for cid, y, item in zip(source_ids, left_ys, sources):
        add_diagram_object(
            view, cid, x=left_x, y=y, w=side_box_width, h=side_box_height,
            text=label_expression(item),
        )

    # Targets à droite, taille uniforme
    for cid, y, item in zip(target_ids, right_ys, targets):
        add_diagram_object(
            view, cid, x=right_x, y=y, w=side_box_width, h=side_box_height,
            text=label_expression(item),
        )

    # ------------------------------------------------------------------
    # 4. Connexions graphiques (toutes labellisées "<<Costream>>")
    # ------------------------------------------------------------------

    target_connection_ids = {eid: [] for eid in graphical_id_of}

    def add_connection(rel_id, src_model_id, tgt_model_id):
        conn_id = new_id()
        src_obj = diagram_obj_of[src_model_id]
        conn = ET.SubElement(src_obj, "sourceConnection", {
            "xsi:type": "archimate:Connection",
            "id": conn_id,
            "textPosition": "0",
            "source": graphical_id_of[src_model_id],
            "target": graphical_id_of[tgt_model_id],
            "archimateRelationship": rel_id,
        })
        ET.SubElement(conn, "feature", {"name": "labelExpression", "value": CONNECTION_LABEL})
        target_connection_ids[tgt_model_id].append(conn_id)

    for rel_id, cid in zip(source_rel_ids, source_ids):
        add_connection(rel_id, cid, app_id)

    for rel_id, cid in zip(target_rel_ids, target_ids):
        add_connection(rel_id, app_id, cid)

    for element_id, conn_ids in target_connection_ids.items():
        if conn_ids:
            obj = diagram_obj_of[element_id]
            old_attrib = dict(obj.attrib)
            obj.attrib.clear()
            obj.set("xsi:type", old_attrib["xsi:type"])
            obj.set("id", old_attrib["id"])
            obj.set("targetConnections", " ".join(conn_ids))
            if "font" in old_attrib:
                obj.set("font", old_attrib["font"])
            if "textPosition" in old_attrib:
                obj.set("textPosition", old_attrib["textPosition"])
            obj.set("archimateElement", old_attrib["archimateElement"])

    # ------------------------------------------------------------------
    # 5. Écriture du fichier
    # ------------------------------------------------------------------

    _indent(model)
    tree = ET.ElementTree(model)
    tree.write(output_path, encoding="UTF-8", xml_declaration=True)
    return output_path


def _indent(elem, level=0):
    """Indentation manuelle (compatible Python < 3.9, pas de ET.indent)."""
    i = "\n" + level * "  "
    children = list(elem)
    if children:
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for idx, child in enumerate(children):
            _indent(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = i + "  " if idx < len(children) - 1 else i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


# ----------------------------------------------------------------------
# Export visuel (SVG / PNG) - sans ouvrir Archi
# ----------------------------------------------------------------------
#
# Archi lui-même n'a pas de mode "headless" accessible ici, donc ce
# script ne peut pas appeler Archi pour produire l'export PNG officiel.
# À la place, gen_schema_image() redessine EXACTEMENT le même layout
# (mêmes calculs que gen_schema, via _compute_layout) en SVG natif
# (aucune dépendance), puis tente une conversion en PNG si une
# bibliothèque de rendu est disponible (cairosvg). Sans cairosvg,
# seul le fichier .svg est produit (lisible dans n'importe quel
# navigateur ou visionneuse d'images).

BOX_FILL_APP = "#ffd9a0"
BOX_FILL_SOURCE = "#d9eaff"
BOX_FILL_TARGET = "#d9ffd9"
BOX_STROKE = "#666666"
ARROW_COLOR = "#444444"


def _svg_escape(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _svg_box(x, y, w, h, fill, title, label, title_size=13, label_size=11):
    title_y = y + h / 2 - (4 if label else -4)
    label_y = y + h / 2 + 16
    parts = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" ry="6" '
        f'fill="{fill}" stroke="{BOX_STROKE}" stroke-width="1.5" />'
    ]
    if title:
        parts.append(
            f'<text x="{x + w / 2}" y="{title_y}" text-anchor="middle" '
            f'font-family="Arial, sans-serif" font-size="{title_size}" '
            f'font-weight="bold" fill="#222222">{_svg_escape(title)}</text>'
        )
    if label:
        parts.append(
            f'<text x="{x + w / 2}" y="{label_y}" text-anchor="middle" '
            f'font-family="Arial, sans-serif" font-size="{label_size}" '
            f'fill="#444444">{_svg_escape(label)}</text>'
        )
    return "\n".join(parts)


def _svg_arrow(x1, y1, x2, y2, label):
    mid_x = (x1 + x2) / 2
    mid_y = (y1 + y2) / 2 - 8
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="{ARROW_COLOR}" stroke-width="1.6" marker-end="url(#arrowhead)" />'
        f'<text x="{mid_x}" y="{mid_y}" text-anchor="middle" '
        f'font-family="Arial, sans-serif" font-size="10" font-style="italic" '
        f'fill="{ARROW_COLOR}">{_svg_escape(label)}</text>'
    )


def gen_schema_image(app, sources, targets, output_path="diagram.png", margin=40):
    """
    Génère un rendu visuel (image) du même diagramme que gen_schema(),
    SANS ouvrir Archi. Produit un fichier .svg (toujours) et tente une
    conversion en .png si `output_path` se termine par ".png" et que
    la bibliothèque `cairosvg` est disponible.

    Retourne le chemin du fichier réellement écrit (.svg si la
    conversion PNG n'a pas pu être effectuée).
    """
    layout = _compute_layout(app, sources, targets)
    side_w = layout["side_box_width"]
    side_h = layout["side_box_height"]
    app_w = layout["app_width"]
    app_h = layout["app_height"]
    app_x = layout["app_x"]
    app_y = layout["app_y"]
    left_x = layout["left_x"]
    left_ys = layout["left_ys"]
    right_x = layout["right_x"]
    right_ys = layout["right_ys"]

    all_bottoms = (
        [y + side_h for y in left_ys]
        + [y + side_h for y in right_ys]
        + [app_y + app_h]
    )
    canvas_w = right_x + side_w + margin
    canvas_h = max(all_bottoms) + margin if all_bottoms else 400

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" '
        f'height="{canvas_h}" viewBox="0 0 {canvas_w} {canvas_h}">',
        '<defs>',
        '  <marker id="arrowhead" markerWidth="10" markerHeight="7" '
        'refX="9" refY="3.5" orient="auto">',
        f'    <polygon points="0 0, 10 3.5, 0 7" fill="{ARROW_COLOR}" />',
        '  </marker>',
        '</defs>',
        f'<rect x="0" y="0" width="{canvas_w}" height="{canvas_h}" fill="white" />',
    ]

    # Flèches sources -> app (point d'ancrage au même niveau Y que la boîte source)
    for y in left_ys:
        anchor_y = y + side_h / 2
        svg_parts.append(_svg_arrow(left_x + side_w, anchor_y, app_x, anchor_y, CONNECTION_LABEL))

    # Flèches app -> targets
    for y in right_ys:
        anchor_y = y + side_h / 2
        svg_parts.append(_svg_arrow(app_x + app_w, anchor_y, right_x, anchor_y, CONNECTION_LABEL))

    # Boîtes
    for item, y in zip(sources, left_ys):
        svg_parts.append(_svg_box(left_x, y, side_w, side_h, BOX_FILL_SOURCE,
                                   item.get("title", ""), item.get("label", "")))
    for item, y in zip(targets, right_ys):
        svg_parts.append(_svg_box(right_x, y, side_w, side_h, BOX_FILL_TARGET,
                                   item.get("title", ""), item.get("label", "")))
    svg_parts.append(_svg_box(app_x, app_y, app_w, app_h, BOX_FILL_APP,
                               app.get("title", ""), app.get("label", ""),
                               title_size=15, label_size=12))

    svg_parts.append("</svg>")
    svg_content = "\n".join(svg_parts)

    svg_path = output_path if output_path.lower().endswith(".svg") else output_path.rsplit(".", 1)[0] + ".svg"
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg_content)

    if output_path.lower().endswith(".png"):
        try:
            import cairosvg  # nécessite : pip install cairosvg --break-system-packages
            cairosvg.svg2png(url=svg_path, write_to=output_path, scale=2)
            return output_path
        except ImportError:
            print(
                "cairosvg n'est pas installé : impossible de convertir en PNG. "
                f"Le rendu SVG a été écrit à la place : {svg_path}\n"
                "Pour activer l'export PNG : pip install cairosvg --break-system-packages"
            )
            return svg_path

    return svg_path


# ----------------------------------------------------------------------
# Exemple d'utilisation
# ----------------------------------------------------------------------

if __name__ == "__main__":
    app = {"title": "MonApp", "label": "Application centrale de traitement"}

    sources = [
        {"title": "SourceApp 1", "label": "Flux client"},
        {"title": "SourceApp 2", "label": "Flux commandes"},
        {"title": "SourceApp 3", "label": "Référentiel produit"},
        {"title": "SourceApp 4", "label": "Données de paiement très détaillées"},
        {"title": "SourceApp 5", "label": "Logs"},
    ]

    targets = [
        {"title": "CibleApp 1", "label": "Reporting"},
        {"title": "CibleApp 2", "label": "Archivage"},
        {"title": "CibleApp 3", "label": "Notification"},
        {"title": "CibleApp 4", "label": "Analytique"},
    ]

    path = gen_schema(app, sources, targets, output_path="flux_mon_app.archimate")
    print(f"Fichier généré : {path}")

    image_path = gen_schema_image(app, sources, targets, output_path="diagram.png")
    print(f"Image générée : {image_path}")
