#!/usr/bin/env python3
"""
Script de migração de conteúdo WordPress → Eleventy
Extrai conteúdo dos ficheiros HTML e cria ficheiros Markdown.
"""

import re
import html
import os
import shutil
import json
from bs4 import BeautifulSoup, NavigableString, Tag

BASE_DIR = "/dados/projetos/tempoelugar"
OUTPUT_DIR = f"{BASE_DIR}/src/posts"
IMAGES_DIR = f"{BASE_DIR}/src/assets/images"
UPLOADS_DIR = f"{BASE_DIR}/wp-content/uploads/2023/05"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)


def clean_filename(path):
    """Remove thumbnail suffix from filename: image-1024x574.jpg → image.jpg"""
    filename = os.path.basename(path)
    return re.sub(r'-\d+x\d+(\.\w+)$', r'\1', filename)


def fix_img(tag):
    """Clean up a BeautifulSoup img tag in place."""
    # Choose best src: prefer data-src (original lazy load) over src (thumbnail)
    data_src = tag.get("data-src", "")
    src = tag.get("src", "")

    # Find the wp-content path
    wp_path = data_src if "/wp-content/uploads/" in data_src else src

    if "/wp-content/uploads/" in wp_path:
        fname = clean_filename(wp_path)
        tag["src"] = f"/assets/images/{fname}"
    elif src.startswith("data:"):
        # Placeholder SVG with no real src — try data-src
        tag["src"] = f"/assets/images/{clean_filename(data_src)}" if data_src else ""

    # Remove WP-specific attributes
    for attr in ["data-src", "srcset", "data-srcset", "sizes", "data-sizes",
                 "fetchpriority", "decoding", "data-ast-blocks-layout",
                 "data-smush-placeholder-width", "style",
                 "data-smush-original-src"]:
        tag.attrs.pop(attr, None)

    # Clean class list
    classes = [c for c in tag.get("class", []) if not re.match(r'^(wp-image-\d+|size-\w+|lazyload|lazyloading|uag-image-\d+)$', c)]
    if classes:
        tag["class"] = classes
    else:
        tag.attrs.pop("class", None)

    # Ensure loading=lazy
    if not tag.get("loading"):
        tag["loading"] = "lazy"


def collect_images(soup_content):
    """Return set of original filenames referenced in the content."""
    images = set()
    for img in soup_content.find_all("img"):
        for attr in ["src", "data-src"]:
            val = img.get(attr, "")
            if "/wp-content/uploads/" in val:
                images.add(clean_filename(val))
    return images


def copy_images(filenames):
    """Copy image files from uploads to assets/images/."""
    for fname in filenames:
        src = f"{UPLOADS_DIR}/{fname}"
        dst = f"{IMAGES_DIR}/{fname}"
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)


def convert_media_text(block):
    """Convert a wp-block-media-text div to simple figure + paragraphs."""
    result = []
    figure = block.find("figure", class_="wp-block-media-text__media")
    text_div = block.find("div", class_="wp-block-media-text__content")

    if figure:
        img = figure.find("img")
        if img:
            fix_img(img)
            new_fig = BeautifulSoup(f"<figure>{img}</figure>", "html.parser")
            result.append(str(new_fig))

    if text_div:
        for child in text_div.children:
            if isinstance(child, Tag):
                result.append(str(child))
            elif isinstance(child, NavigableString) and child.strip():
                result.append(f"<p>{child.strip()}</p>")

    return "\n".join(result)


def extract_content(soup):
    """
    Walk entry-content and produce clean HTML, stripping WP/UAGB wrappers
    but preserving semantic content.
    """
    entry = soup.find("div", class_=re.compile(r"entry-content"))
    if not entry:
        return ""

    parts = []

    def walk(node):
        if isinstance(node, NavigableString):
            text = node.strip()
            if text:
                parts.append(f"<p>{text}</p>")
            return

        if not isinstance(node, Tag):
            return

        cls = " ".join(node.get("class", []))
        tag = node.name

        # Skip invisible/utility elements
        if tag in ("noscript", "script", "style", "form", "nav"):
            return

        # --- Headings: keep as-is, strip classes ---
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            text = node.get_text(strip=True)
            if text:
                parts.append(f"<{tag}>{text}</{tag}>")
            return

        # --- Paragraphs ---
        if tag == "p":
            inner = node.decode_contents()
            if inner.strip():
                parts.append(f"<p>{inner}</p>")
            return

        # --- HR ---
        if tag == "hr":
            parts.append("<hr>")
            return

        # --- Images ---
        if tag == "img":
            fix_img(node)
            if node.get("src") and not node["src"].startswith("data:"):
                parts.append(str(node))
            return

        # --- Figures (standard WP image block) ---
        if tag == "figure":
            img = node.find("img")
            if img:
                fix_img(img)
                caption = node.find("figcaption")
                cap_text = caption.get_text(strip=True) if caption else ""
                alt = img.get("alt", "")
                if cap_text and not alt:
                    img["alt"] = cap_text
                if cap_text:
                    parts.append(f"<figure>{img}<figcaption>{cap_text}</figcaption></figure>")
                else:
                    parts.append(f"<figure>{img}</figure>")
            return

        # --- Media text blocks ---
        if "wp-block-media-text" in cls:
            parts.append(convert_media_text(node))
            return

        # --- Lists ---
        if tag in ("ul", "ol"):
            parts.append(str(node))
            return

        # --- Buttons/links that are CTAs — skip ---
        if "uagb-infobox-cta-link" in cls or "wp-block-button" in cls:
            return

        # --- Generic: recurse into children ---
        for child in node.children:
            walk(child)

    walk(entry)

    content = "\n".join(parts)
    # Collapse 3+ newlines to 2
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def find_featured_image(content_html):
    """Find the first non-logo image src."""
    matches = re.findall(r'src="(/assets/images/([^"]+))"', content_html)
    for path, fname in matches:
        if "banner300" not in fname and "banner800" not in fname:
            return path
    return None


# Post definitions with metadata
POSTS = [
    {
        "slug": "paris-em-1789-a-revolucao-francesa",
        "date": "2023-05-04",
        "categories": ["Passado histórico"],
        "tags": ["franca", "seculo-xviii", "revolucao-francesa"],
    },
    {
        "slug": "viagem-no-tempo-ate-viena-em-1789",
        "date": "2023-05-03",
        "categories": ["Passado histórico"],
        "tags": ["austria", "seculo-xviii"],
    },
    {
        "slug": "lisboa-no-seculo-xviii-a-minha-chegada",
        "date": "2023-05-08",
        "categories": ["Passado histórico"],
        "tags": ["portugal", "seculo-xviii", "lisboa"],
    },
    {
        "slug": "a-minha-jornada-por-nova-iorque-em-1920",
        "date": "2023-05-06",
        "categories": ["Passado histórico"],
        "tags": ["eua", "seculo-xx", "nova-iorque"],
    },
    {
        "slug": "batalha-de-aljubarrota-o-esplendor-e-a-coragem",
        "date": "2023-05-10",
        "categories": ["Passado histórico"],
        "tags": ["portugal", "medieval", "batalha"],
    },
    {
        "slug": "uma-jornada-pelas-ruas-de-salzinnes-em-1823",
        "date": "2023-05-11",
        "categories": ["Passado histórico"],
        "tags": ["belgica", "seculo-xix"],
    },
    {
        "slug": "neuschwanstein-uma-viagem-ao-castelo-dos-sonhos",
        "date": "2023-05-12",
        "categories": ["Europa Medieval e Moderna"],
        "tags": ["alemanha", "castelo", "seculo-xix"],
    },
    {
        "slug": "as-maravilhas-de-bruges-uma-jornada-no-tempo",
        "date": "2023-05-13",
        "categories": ["Europa Medieval e Moderna"],
        "tags": ["belgica", "medieval"],
    },
    {
        "slug": "uma-viagem-epica-ao-coracao-da-renascenca",
        "date": "2023-05-14",
        "categories": ["Europa Medieval e Moderna"],
        "tags": ["italia", "florenca", "renascenca"],
    },
    {
        "slug": "o-vale-do-lapedo-ha-30-000-anos",
        "date": "2023-05-07",
        "categories": ["Passado histórico"],
        "tags": ["portugal", "prehistoria", "arqueologia"],
    },
    {
        "slug": "experimentei-a-comida-em-londres-em-2060",
        "date": "2023-05-01",
        "categories": ["Futuro"],
        "tags": ["reino-unido", "futuro", "2060"],
    },
    {
        "slug": "a-viagem-ao-futuro-a-cidade-de-lviv-ucrania",
        "date": "2023-05-02",
        "categories": ["Futuro"],
        "tags": ["ucrania", "futuro"],
    },
    {
        "slug": "aventurando-me-no-futuro-em-toquio",
        "date": "2023-05-05",
        "categories": ["Futuro"],
        "tags": ["japao", "toquio", "futuro"],
    },
    {
        "slug": "uma-viagem-espacial-ao-futuro",
        "date": "2023-05-09",
        "categories": ["Futuro"],
        "tags": ["espaco", "futuro", "tecnologia"],
    },
    {
        "slug": "uma-jornada-fascinante-por-cressoria-em-2215",
        "date": "2023-05-23",
        "categories": ["Futuro"],
        "tags": ["futuro", "2215", "ficcao"],
    },
    {
        "slug": "praga-uma-aventura-encantadora",
        "date": "2023-05-29",
        "categories": ["Europa Medieval e Moderna"],
        "tags": ["republica-checa", "praga", "historia"],
    },
]


def process_post(post_info):
    slug = post_info["slug"]
    filepath = f"{BASE_DIR}/{slug}/index.html"

    if not os.path.exists(filepath):
        print(f"  SKIP (not found): {slug}")
        return

    with open(filepath, encoding="utf-8") as f:
        raw = f.read()

    soup = BeautifulSoup(raw, "html.parser")

    # Title
    h1 = soup.find("h1", class_=re.compile(r"entry-title"))
    title = h1.get_text(strip=True) if h1 else slug

    # Description
    desc_tag = soup.find("meta", {"name": "description"})
    description = desc_tag.get("content", "") if desc_tag else ""

    # Collect images before processing
    entry = soup.find("div", class_=re.compile(r"entry-content"))
    if entry:
        copy_images(collect_images(entry))

    # Extract content
    content = extract_content(soup)

    # Featured image (first non-logo img after conversion)
    featured_image = find_featured_image(content)

    # Front matter
    cats = json.dumps(post_info.get("categories", []), ensure_ascii=False)
    tags = json.dumps(post_info.get("tags", []), ensure_ascii=False)
    featured_line = f'featuredImage: "{featured_image}"' if featured_image else ""

    frontmatter = f"""---
title: "{title.replace('"', "'")}"
date: {post_info["date"]}
description: "{description.replace('"', "'")}"
{featured_line}
categories: {cats}
tags: {tags}
layout: post.njk
---
"""

    out_path = f"{OUTPUT_DIR}/{slug}.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(frontmatter)
        f.write("\n")
        f.write(content)

    print(f"  OK: {slug}")
    if featured_image:
        print(f"      featured: {featured_image}")


print("=== Migrating posts ===")
for post in POSTS:
    process_post(post)

print("\n=== Copying common images ===")
common_images = [
    "banner300.png", "banner800.png", "corvina.jpg", "corvinatop.jpg",
    "corvinavign.jpg", "jorgecorvina_573.jpg", "jorgeatrabalhar.jpg",
    "maquina.jpg", "maquinagrande.jpg", "maquinapinhal.jpg",
    "diagramageral.jpg", "diagramalateral.jpg", "constrmaquina.jpg",
    "estacao.jpg", "curiosidades1.jpg", "curiosidades2.jpg",
    "equipa.jpg", "hotel.jpg", "hotel-1.jpg", "alojam.jpg",
    "selfie.jpg", "restaur.jpg", "viagem.jpg",
]
for img in common_images:
    src = f"{UPLOADS_DIR}/{img}"
    dst = f"{IMAGES_DIR}/{img}"
    if os.path.exists(src) and not os.path.exists(dst):
        shutil.copy2(src, dst)
        print(f"  Copied: {img}")
    elif not os.path.exists(src):
        print(f"  Missing: {img}")

print("\nDone.")
