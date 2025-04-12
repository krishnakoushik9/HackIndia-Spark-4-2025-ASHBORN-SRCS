import os
import asyncio
from typing import List
from unstructured.partition.auto import partition

class DocumentProcessor:
    def __init__(self, vector_store, llm_client):
        """
        Initializes the DocumentProcessor.

        :param vector_store: An object responsible for storing document vectors.
        :param llm_client: Not currently used, but included for future integration.
        """
        self.vector_store = vector_store
        self.llm_client = llm_client

    async def process_folders(self, folder_paths: List[str]) -> int:
        """
        Processes all supported files in the given folder paths asynchronously.

        :param folder_paths: A list of folder paths to scan.
        :return: Total number of supported files processed.
        """
        all_files = []
        for folder in folder_paths:
            for root, _, files in os.walk(folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    if self._is_supported_file(file_path):
                        all_files.append(file_path)

        tasks = [self._process_and_store(file) for file in all_files]
        await asyncio.gather(*tasks)
        return len(all_files)

    async def _process_and_store(self, file_path: str):
        """
        Processes a single file and adds it to the vector store.

        :param file_path: Full path of the file to process.
        """
        try:
            content = await asyncio.to_thread(self.extract_text_sync, file_path)
            if not content or not content.strip():
                print(f"[SKIPPED] Empty or unreadable content in: {file_path}")
                return

            metadata = {
                "filename": os.path.basename(file_path),
                "path": file_path
            }

            result = self.vector_store.add_document(file_path, content, metadata)
            if not result:
                print(f"[FAIL] Failed to add: {file_path}")
        except Exception as e:
            print(f"[ERROR] Error processing {file_path}: {e}")

    def extract_text_sync(self, file_path: str) -> str:
        """
        Synchronously extracts text from a file using unstructured's partition.

        :param file_path: Path to the document.
        :return: Extracted text as a string.
        """
        elements = partition(filename=file_path)
        return "\n".join([el.text for el in elements if el.text is not None])

    async def extract_text(self, file_path: str) -> str:
        """
        Public method expected by backend to extract text from a file.
        Wraps around the existing sync method for compatibility.

        :param file_path: Path to the document.
        :return: Extracted text.
        """
        return await asyncio.to_thread(self.extract_text_sync, file_path)

    def _is_supported_file(self, file_path: str) -> bool:
        """
        Checks if a file has a supported extension.

        :param file_path: Full file path.
        :return: True if the file is supported, else False.
        """
        supported_exts = (
            ".pdf", ".docx", ".pptx", ".txt", ".eml", ".html", ".md", ".jpg", ".png"
        )
        return file_path.lower().endswith(supported_exts)
