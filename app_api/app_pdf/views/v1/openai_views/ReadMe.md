# How to test locally before deploying to OpenAI


1. In the Web UI create a new account with an enterprise subscription and generate an API key.
```bash
export TOKEN="zZ---123="
```

2. view_pdf_convert_to_image
```bash
curl -X POST "http://localhost:9000/pdf/v1/convert-to-image/openai" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
        "openaiFileIdRefs": [
          {
            "name": "my_pdf_file.pdf",
            "id": "file-testid",
            "mime_type": "application/pdf",
            "download_link": "{any_pdf_file_download_link}"
          }
        ]
      }'
```

3. view_pdf_convert_to_word_pro
```bash
curl -X POST "http://localhost:9000/pdf/v1/convert-to-word-pro/openai" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
        "openaiFileIdRefs": [
          {
            "name": "my_pdf_file.pdf",
            "id": "file-testid",
            "mime_type": "application/pdf",
            "download_link": "{any_pdf_file_download_link}"
          }
        ]
      }'
```

4. view_pdf_delete_pages
```bash
curl -X POST "http://localhost:9000/pdf/v1/delete-pages/openai?pages_to_remove=1,2" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
        "openaiFileIdRefs": [
          {
            "name": "my_pdf_file.pdf",
            "id": "file-testid",
            "mime_type": "application/pdf",
            "download_link": "{any_pdf_file_download_link}"
          }
        ]
      }'
```

5. view_pdf_extract_images
```bash
curl -X POST "http://localhost:9000/pdf/v1/extract-images/openai" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
        "openaiFileIdRefs": [
          {
            "name": "my_pdf_file.pdf",
            "id": "file-testid",
            "mime_type": "application/pdf",
            "download_link": "{any_pdf_file_download_link}"
          }
        ]
      }'
```

6. view_pdf_insert_pdf
```bash
curl -X POST "http://localhost:9000/pdf/v1/insert-pdf/openai?after_page_number=1" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
        "openaiFileIdRefs": [
          {
            "name": "test1.pdf",
            "id": "file-testid",
            "mime_type": "application/pdf",
            "download_link": "{any_pdf_file_download_link}"
          },
          {
            "name": "test2.pdf",
            "id": "file-testid",
            "mime_type": "application/pdf",
            "download_link": "{any_pdf_file_download_link}"
          }
        ]
      }'
```

7. view_pdf_merge_images
```bash
curl -X POST "http://localhost:9000/pdf/v1/merge-images/openai?use_upload_order=false" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
        "openaiFileIdRefs": [
          {
            "name": "test1.jpg",
            "id": "file-testid",
            "mime_type": "image/jpeg",
            "download_link": "{any_jpeg_file_download_link}"
          },
          {
            "name": "test2.jpg",
            "id": "file-testid2",
            "mime_type": "image/jpeg",
            "download_link": "{any_jpeg_file_download_link}"
          }
        ]
      }'
```

8. view_pdf_merge_pdfs
```bash
curl -X POST "http://localhost:9000/pdf/v1/merge-pdfs/openai?use_upload_order=false" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
        "openaiFileIdRefs": [
          {
            "name": "my_pdf_file.pdf",
            "id": "file-testid",
            "mime_type": "application/pdf",
            "download_link": "{any_pdf_file_download_link}"
          },
          {
            "name": "my_pdf_file.pdf",
            "id": "file-testid",
            "mime_type": "application/pdf",
            "download_link": "{any_pdf_file_download_link}"
          }
        ]
      }'
```

9. view_pdf_page_order
```bash
curl -X POST "http://localhost:9000/pdf/v1/page-order/openai?page_order=4,3,2,1" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
        "openaiFileIdRefs": [
          {
            "name": "my_pdf_file.pdf",
            "id": "file-testid",
            "mime_type": "application/pdf",
            "download_link": "{any_pdf_file_download_link}"
          }
        ]
      }'
```

10. view_pdf_password_management_add
```bash
curl -X POST "http://localhost:9000/pdf/v1/add-password/openai" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "my_password",
      "openaiFileIdRefs": [
        {
          "name": "my_pdf_file.pdf",
          "id": "file-testid",
          "mime_type": "application/pdf",
          "download_link": "{any_pdf_file_download_link}"
        }
      ]
  }'
```

11. view_pdf_password_management_change
```bash
curl -X POST "http://localhost:9000/pdf/v1/change-password/openai" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
      "old_password": "my_password",
      "new_password": "my_password",
      "openaiFileIdRefs": [
        {
          "name": "my_pdf_file.pdf",
          "id": "file-testid",
          "mime_type": "application/pdf",
          "download_link": "{any_pdf_file_download_link}"
        }
      ]
  }'
```

12. view_pdf_password_management_remove
```bash
curl -X POST "http://localhost:9000/pdf/v1/remove-password/openai" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
      "password": "my_password",
      "openaiFileIdRefs": [
        {
          "name": "my_pdf_file.pdf",
          "id": "file-testid",
          "mime_type": "application/pdf",
          "download_link": "{any_pdf_file_download_link}"
        }
      ]
  }'
```

13. view_pdf_rotate
```bash
curl -X POST "http://localhost:9000/pdf/v1/rotate/openai?pages_to_rotate_right=1,2&pages_to_rotate_left=3,4&pages_to_rotate_upside_down=5,6" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
      "openaiFileIdRefs": [
        {
          "name": "my_pdf_file.pdf",
          "id": "file-testid",
          "mime_type": "application/pdf",
          "download_link": "{any_pdf_file_download_link}"
        }
      ]
  }'
```

14. view_pdf_split
```bash
curl -X POST "http://localhost:9000/pdf/v1/split/openai" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
      "openaiFileIdRefs": [
        {
          "name": "my_pdf_file.pdf",
          "id": "file-testid",
          "mime_type": "application/pdf",
          "download_link": "{any_pdf_file_download_link}"
        }
      ]
  }'
```

15. view_pdf_watermark_image
```bash
curl -X POST "http://localhost:9000/pdf/v1/watermark-image/openai?grid_rows=1&grid_columns=1&image_scale=0.17&transparency=0.5" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
      "openaiFileIdRefs": [
        {
            "name": "tree.jpg",
            "id": "file-testid",
            "mime_type": "image/jpeg",
            "download_link": "{any_jpeg_file_download_link}"
          },
        {
          "name": "my_pdf_file.pdf",
          "id": "file-testid",
          "mime_type": "application/pdf",
          "download_link": "{any_pdf_file_download_link}"
        }
      ]
  }'
```

16. view_pdf_watermark_text
```bash
curl -X POST "http://localhost:9000/pdf/v1/watermark-text/openai?text=132&grid_rows=1&grid_columns=1&rgb_text_color=0,255,255&transparency=0.5&rotation_angle=45" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
      "openaiFileIdRefs": [
        {
          "name": "my_pdf_file.pdf",
          "id": "file-testid",
          "mime_type": "application/pdf",
          "download_link": "{any_pdf_file_download_link}"
        }
      ]
  }'
```