#!/usr/bin/env python3
"""panel/ papkasidan PodcastSuite.ccx yasaydi.

.ccx — bu oddiy ZIP arxiv, faqat kengaytmasi boshqacha. Ichida
manifest.json ENG YUQORI qavatda turishi shart, aks holda Adobe
o'rnatuvchisi paketni tanimaydi.

Ilgari bu faylni UXP Developer Tools orqali qo'lda yasash kerak edi
(••• > Package). Endi shart emas — paket repo bilan birga keladi va
o'rnatuvchi uni o'zi topadi.
"""

import json
import os
import sys
import zipfile

BU = os.path.dirname(os.path.abspath(__file__))
PANEL = os.path.join(BU, "panel")
CHIQISH = os.path.join(BU, "PodcastSuite.ccx")


def yasash():
    manifest = os.path.join(PANEL, "manifest.json")
    if not os.path.isfile(manifest):
        print("[XATO] panel/manifest.json topilmadi")
        return 1
    with open(manifest, encoding="utf-8") as fh:
        info = json.load(fh)

    # Fayllarni tartib bilan yozamiz: bir xil kirishdan bir xil chiqish
    # bo'lsin, aks holda har yasashda .ccx «o'zgargan» bo'lib ko'rinadi
    # va git tarixini keraksiz to'ldiradi.
    fayllar = []
    for ildiz, _, nomlar in os.walk(PANEL):
        for nom in sorted(nomlar):
            # sinov.js — ishlab chiqish qurilmasi, Premiere'ga kerak emas
            if (nom.startswith(".") or nom.endswith((".pyc", ".map"))
                    or nom == "sinov.js"):
                continue
            tola = os.path.join(ildiz, nom)
            fayllar.append((tola, os.path.relpath(tola, PANEL)))
    fayllar.sort(key=lambda x: x[1])

    if not any(n == "manifest.json" for _, n in fayllar):
        print("[XATO] manifest.json arxiv ildizida bo'lishi kerak")
        return 1

    with zipfile.ZipFile(CHIQISH, "w", zipfile.ZIP_DEFLATED) as z:
        for tola, nom in fayllar:
            # Sanani qotiramiz — natija takrorlanadigan bo'lsin
            zi = zipfile.ZipInfo(nom, date_time=(2026, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            with open(tola, "rb") as fh:
                z.writestr(zi, fh.read())

    olcham = os.path.getsize(CHIQISH) / 1024.0
    print(f"PodcastSuite.ccx yasaldi — {info['name']} v{info['version']}, "
          f"{len(fayllar)} fayl, {olcham:.0f} KB")
    print(f"  {CHIQISH}")
    return 0


if __name__ == "__main__":
    sys.exit(yasash())
