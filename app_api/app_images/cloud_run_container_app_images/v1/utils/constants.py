IMAGE_FILE_EXTENSIONS = {
	"jpeg", "jpg", "jpe",  # JPEG
	"png",  # PNG
	"gif",  # GIF
	"bmp", "dib",  # BMP
	"tiff", "tif",  # TIFF
	"webp",  # WebP
	"ppm", "pgm", "pbm",  # Portable_Pixmap,Portable_Graymap,Portable_Bitmap
	"tga"  # Targa Image File
}

FORMAT_MAPPING_FOR_PILLOW = {
	'jpeg': 'JPEG',
	'jpg': 'JPEG',
	'jpe': 'JPEG',  # Additional JPEG extension
	'png': 'PNG',
	'gif': 'GIF',
	'bmp': 'BMP',
	'dib': 'BMP',  # Device Independent Bitmap, also uses the BMP format
	'tiff': 'TIFF',
	'tif': 'TIFF',
	'webp': 'WEBP',
	'ppm': 'PPM',  # Portable Pixmap
	'pgm': 'PGM',  # Portable Graymap
	'pbm': 'PBM',  # Portable Bitmap
	'tga': 'TGA'  # Targa
}

# view_image_convert_format
CONVERT_MATRIX = {
	"pillow": {
		"jpeg": IMAGE_FILE_EXTENSIONS - {"jpeg", "gif"},
		"jpg": IMAGE_FILE_EXTENSIONS - {"jpg", "gif"},
		"jpe": IMAGE_FILE_EXTENSIONS - {"jpe", "gif"},
		"png": IMAGE_FILE_EXTENSIONS - {"png", "gif"},
		"gif": IMAGE_FILE_EXTENSIONS,
		"bmp": IMAGE_FILE_EXTENSIONS - {"bmp", "gif"},
		"dib": IMAGE_FILE_EXTENSIONS - {"dib", "gif"},
		"tiff": IMAGE_FILE_EXTENSIONS - {"tiff", "gif"},
		"tif": IMAGE_FILE_EXTENSIONS - {"tif", "gif"},
		"webp": IMAGE_FILE_EXTENSIONS - {"webp", "gif"},
		"ppm": IMAGE_FILE_EXTENSIONS - {"ppm", "gif"},
		"pgm": IMAGE_FILE_EXTENSIONS - {"pgm", "gif"},
		"pbm": IMAGE_FILE_EXTENSIONS - {"pbm", "gif"},
		"tga": IMAGE_FILE_EXTENSIONS - {"tga", "gif"},
	},
	"imagemagick": {
		"heic": IMAGE_FILE_EXTENSIONS - {"gif"},
		"heif": IMAGE_FILE_EXTENSIONS - {"gif"},
		"raw": IMAGE_FILE_EXTENSIONS - {"gif"},
	},
	"cairosvg": {
		"svg": {"png", },
	}
}
