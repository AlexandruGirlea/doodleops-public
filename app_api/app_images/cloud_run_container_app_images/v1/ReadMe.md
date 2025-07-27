# Cloud Run Container App Images API - v1.5.0

## Example: /image/create-qr-code
How to create a QR code image using the API.

Step 1: Make sure you have the API running locally or on a server.
```bash
make build cont=app_images_v1
make up cont=app_images_v1
make run cont=app_images_v1
```

Step 2: Call the API endpoint to create a QR code image.
```bash
curl --location --request POST 'http://localhost:8080/image/create-png-qr-code' \
--header 'Authorization: Bearer gAAAAABmVBX7pR1x6li123GT5aH213b8leXYZgjA_Tn-b0rMIw==' \
-F 'text=E' \
-F 'scale=20' \
-F 'output_format=PNG' \
-F 'fill_color=000000' \
-F 'background_color=FFFFFF' \
-F 'error_correction_level=15' -F 'file=@/Users/alex_g/Downloads/fruit-123.png' \
--output ~/Desktop/test.png
  
curl --location --request POST 'http://localhost:8080/image/create-png-qr-code' \
--header 'Authorization: Bearer gAAAAABmVBX7pR1x6lim123pC4sUnU123YZgjA_Tn-b0rMIw==' \
-F 'text=E' \
-F 'scale=20' \
-F 'output_format=SVG' \
-F 'fill_color=000000' \
-F 'background_color=FFFFFF' \
-F 'error_correction_level=15' -F 'file=@/Users/alex_g/Downloads/fruit-123.png' \
--output ~/Desktop/test.svg
```