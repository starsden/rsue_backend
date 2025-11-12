import barcode
from barcode.writer import ImageWriter
from pathlib import Path
def generate_barcode(number: str, output_path: str = 'ean13_barcode') -> str:
    output = Path(output_path).resolve()
    EAN = barcode.get_barcode_class('ean13')
    ean = EAN(number, writer=ImageWriter())
    filename = ean.save(str(output))
    return str(filename)