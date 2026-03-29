def _on_save_clicked(self) -> None:
        data = self.form.get_data()
        
        if not data["title"]:
            self.form.display_name_input.setFocus()
            return

        try:
            self.save_btn.setEnabled(False)
            self.save_btn.setText(self.translator.tr("upload.saving"))
            self.save_btn.repaint()
            
            encryption_key = None
            upload_path = self._file_path
            temp_encrypted_path = None

            if self.is_edit_mode:
                self.resulting_document = self._api.update_document(
                    document_id=self.doc_to_edit.id,
                    title=data["title"],
                    category_id=data["category_id"],
                    file_type_id=data["file_type_id"],
                    is_private=data["is_private"],
                    is_public=data["is_public"],
                    is_public_edit=data["is_public_edit"],
                    is_read_only=data["is_read_only"],
                    notes=data["notes"],
                    tags=data["tags"],
                )
            else:
                # Encrypt new uploads
                try:
                    encryption_key = secrets.token_urlsafe(16)
                    doc = fitz.open(self._file_path)
                    fd, temp_encrypted_path = tempfile.mkstemp(suffix=".pdf")
                    os.close(fd)
                    
                    doc.save(
                        temp_encrypted_path,
                        garbage=4,
                        deflate=True,
                        encrypt=encryption_key
                    )
                    doc.close()
                    upload_path = temp_encrypted_path
                except Exception as e:
                    print(f"Encryption failed, uploading unencrypted: {e}")
                    encryption_key = None
                    upload_path = self._file_path

                try:
                    self.resulting_document = self._api.upload_file(
                        file_path=upload_path,
                        title=data["title"],
                        category_id=data["category_id"],
                        file_type_id=data["file_type_id"],
                        use_ocr=data.get("use_ocr", True),
                        is_private=data["is_private"],
                        is_public=data["is_public"],
                        is_public_edit=data["is_public_edit"],
                        is_read_only=data["is_read_only"],
                        notes=data["notes"],
                        tags=data["tags"],
                        folder_id=data["folder_id"],
                    )
                finally:
                    if temp_encrypted_path and os.path.exists(temp_encrypted_path):
                        try:
                            os.remove(temp_encrypted_path)
                        except:
                            pass

            self.accept()
        except Exception as e:
            print(f"Save error: {e}")
            self.save_btn.setEnabled(True)
            btn_text = self.translator.tr("common.save") if self.is_edit_mode else self.translator.tr("upload.title_upload")
            self.save_btn.setText(btn_text)
            QMessageBox.critical(self, self.translator.tr("common.error"), f"Save failed: {e}")
