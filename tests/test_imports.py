from pathlib import Path
import zipfile

from pipeline.detect import scan
from pipeline.imports import expand_bundles


def test_zip_bundle_is_flattened_normalized_and_idempotent(tmp_path):
    bundle = tmp_path / "havi-exportok.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr(
            "meta/rossz-kiterjesztes.txt",
            "Kampány neve,Eredmény jelzése,Elérés,Megjelenések\nTeszt,reach,10,20\n",
        )
        archive.writestr(
            "scheduler/letoltes.data",
            "Datetime,PostType,FacebookPostIDs,InstagramPostIDs\n"
            "01.07.2026 - 11:00 AM,image,1,2\n",
        )
        archive.writestr("../../README.txt", "nem riportforrás")

    imported = expand_bundles(tmp_path)
    again = expand_bundles(tmp_path)

    assert {path.name for path in imported} == {
        "rossz-kiterjesztes.csv",
        "letoltes.csv",
    }
    assert again == []
    assert {source.kind for source in scan(tmp_path)} == {"meta_ads", "zoomsphere"}
    assert all(path.parent == tmp_path for path in imported)


def test_xlsx_is_not_mistaken_for_an_import_bundle(tmp_path):
    from openpyxl import Workbook

    path = tmp_path / "scheduler.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Datetime", "PostType", "FacebookPostIDs", "InstagramPostIDs"])
    sheet.append(["01.07.2026 - 11:00 AM", "image", "1", "2"])
    workbook.save(path)

    assert expand_bundles(tmp_path) == []
    assert scan(tmp_path)[0].kind == "zoomsphere"
