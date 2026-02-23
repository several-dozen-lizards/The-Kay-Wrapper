"""
UI components for document management.
"""

import customtkinter as ctk
from tkinter import messagebox
from typing import List, Callable, Optional
from document_manager import DocumentManager, DocumentInfo


class DocumentManagerWindow(ctk.CTkToplevel):
    """Main document manager window."""

    def __init__(self, parent, memory_engine, entity_graph):
        super().__init__(parent)

        self.title("Document Manager")
        self.geometry("1200x700")

        self.manager = DocumentManager(memory_engine, entity_graph)
        self.current_documents = []
        self.selected_doc = None

        self._build_ui()
        self._load_documents()

    def _build_ui(self):
        """Build the UI layout."""
        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left panel - Document list
        self.left_panel = ctk.CTkFrame(self, width=350)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.left_panel.grid_rowconfigure(4, weight=1)  # Document list expands

        # Search bar
        self.search_label = ctk.CTkLabel(
            self.left_panel,
            text="Search Documents",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.search_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        self.search_entry = ctk.CTkEntry(
            self.left_panel,
            placeholder_text="🔍 Search by filename...",
            font=ctk.CTkFont(size=14)
        )
        self.search_entry.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._on_search)

        # Sort options
        sort_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        sort_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        sort_label = ctk.CTkLabel(
            sort_frame,
            text="Sort by:",
            font=ctk.CTkFont(size=12)
        )
        sort_label.pack(side="left", padx=(0, 5))

        self.sort_var = ctk.StringVar(value="Date (Newest)")
        self.sort_menu = ctk.CTkOptionMenu(
            sort_frame,
            variable=self.sort_var,
            values=[
                "Date (Newest)",
                "Date (Oldest)",
                "Name (A-Z)",
                "Name (Z-A)",
                "Size (Largest)",
                "Size (Smallest)",
                "Memories (Most)",
                "Memories (Least)"
            ],
            command=self._on_sort_change,
            font=ctk.CTkFont(size=12),
            width=140
        )
        self.sort_menu.pack(side="left", expand=True, fill="x")

        # Select All / Deselect All buttons
        select_button_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        select_button_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

        self.select_all_btn = ctk.CTkButton(
            select_button_frame,
            text="☑ Select All",
            command=self._select_all,
            font=ctk.CTkFont(size=12),
            height=28,
            fg_color="transparent",
            border_width=1
        )
        self.select_all_btn.pack(side="left", padx=2, expand=True, fill="x")

        self.deselect_all_btn = ctk.CTkButton(
            select_button_frame,
            text="☐ Deselect All",
            command=self._deselect_all,
            font=ctk.CTkFont(size=12),
            height=28,
            fg_color="transparent",
            border_width=1
        )
        self.deselect_all_btn.pack(side="left", padx=2, expand=True, fill="x")

        # Document list (scrollable)
        self.doc_list = DocumentList(
            self.left_panel,
            on_select_callback=self._on_document_selected
        )
        self.doc_list.grid(row=4, column=0, padx=10, pady=10, sticky="nsew")

        # Buttons at bottom
        self.button_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.button_frame.grid(row=5, column=0, padx=10, pady=(0, 10), sticky="ew")

        self.refresh_button = ctk.CTkButton(
            self.button_frame,
            text="🔄 Refresh",
            command=self._load_documents,
            font=ctk.CTkFont(size=14)
        )
        self.refresh_button.pack(side="left", padx=5)

        self.delete_button = ctk.CTkButton(
            self.button_frame,
            text="🗑️ Delete Selected",
            command=self._delete_selected,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=ctk.CTkFont(size=14)
        )
        self.delete_button.pack(side="left", padx=5)

        # Right panel - Document details
        self.right_panel = DocumentDetails(self)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)

    def _load_documents(self):
        """Load all documents from storage."""
        self.current_documents = self.manager.load_all_documents()
        self.doc_list.refresh(self.current_documents)

        # Update title with count
        self.title(f"Document Manager ({len(self.current_documents)} documents)")

    def _on_search(self, event):
        """Handle search input."""
        query = self.search_entry.get()
        filtered = self.manager.search_documents(query, self.current_documents)

        # Re-apply current sort
        self._on_sort_change(self.sort_var.get())

    def _on_sort_change(self, choice):
        """Handle sort option change."""
        # Get current filtered documents
        query = self.search_entry.get()
        docs = self.manager.search_documents(query, self.current_documents)

        # Sort based on selection
        if choice == "Date (Newest)":
            docs.sort(key=lambda d: d.import_date, reverse=True)
        elif choice == "Date (Oldest)":
            docs.sort(key=lambda d: d.import_date)
        elif choice == "Name (A-Z)":
            docs.sort(key=lambda d: d.filename.lower())
        elif choice == "Name (Z-A)":
            docs.sort(key=lambda d: d.filename.lower(), reverse=True)
        elif choice == "Size (Largest)":
            docs.sort(key=lambda d: d.file_size, reverse=True)
        elif choice == "Size (Smallest)":
            docs.sort(key=lambda d: d.file_size)
        elif choice == "Memories (Most)":
            docs.sort(key=lambda d: d.memory_count, reverse=True)
        elif choice == "Memories (Least)":
            docs.sort(key=lambda d: d.memory_count)

        # Refresh list with sorted documents
        self.doc_list.refresh(docs)

    def _select_all(self):
        """Select all document checkboxes."""
        self.doc_list.select_all()

    def _deselect_all(self):
        """Deselect all document checkboxes."""
        self.doc_list.clear_selections()

    def _on_document_selected(self, doc_id: str):
        """Handle document selection."""
        # Find selected document
        self.selected_doc = next((d for d in self.current_documents if d.doc_id == doc_id), None)

        if self.selected_doc:
            self.right_panel.display_document(self.selected_doc, self.manager)

    def _delete_selected(self):
        """Delete documents that are checked."""
        # Get checked documents
        selected_doc_ids = self.doc_list.get_selected_for_deletion()

        if not selected_doc_ids:
            messagebox.showwarning("No Selection", "Please check at least one document to delete.")
            return

        # Find full document info for selected doc_ids
        selected_docs = [doc for doc in self.current_documents if doc.doc_id in selected_doc_ids]

        # Show confirmation dialog
        result = DeleteConfirmationDialog(
            self,
            documents=selected_docs
        ).show()

        if result:
            delete_memories = result == "delete_all"

            # Delete each selected document
            successes = []
            errors = []

            for doc in selected_docs:
                success, message = self.manager.delete_document(
                    doc.doc_id,
                    delete_memories=delete_memories
                )

                if success:
                    successes.append(doc.filename)
                else:
                    errors.append(f"{doc.filename}: {message}")

            # Show results
            if successes and not errors:
                messagebox.showinfo("Success", f"Deleted {len(successes)} document(s):\n" + "\n".join(f"✓ {name}" for name in successes))
            elif successes and errors:
                messagebox.showwarning("Partial Success",
                    f"Deleted {len(successes)} document(s):\n" + "\n".join(f"✓ {name}" for name in successes) +
                    f"\n\nErrors ({len(errors)}):\n" + "\n".join(f"✗ {err}" for err in errors))
            else:
                messagebox.showerror("Error", f"Failed to delete all documents:\n" + "\n".join(errors))

            # Refresh and clear
            self._load_documents()
            self.right_panel.clear()
            self.selected_doc = None
            self.doc_list.clear_selections()


class DocumentList(ctk.CTkScrollableFrame):
    """Scrollable list of documents with multi-select checkboxes."""

    def __init__(self, parent, on_select_callback: Callable):
        super().__init__(parent, fg_color="transparent")

        self.on_select_callback = on_select_callback
        self.doc_items = []  # Store (frame, button, checkbox, doc_id) tuples
        self.selected_doc_id = None

    def refresh(self, documents: List[DocumentInfo]):
        """Rebuild list with new documents."""
        # Clear existing items
        for item_frame, btn, checkbox, doc_id in self.doc_items:
            item_frame.destroy()
        self.doc_items = []

        # Create item for each document
        for doc in documents:
            # Status indicator
            status_emoji = {
                'complete': '✅',
                'partial': '⚠️',
                'failed': '❌'
            }.get(doc.import_status, '📄')

            # Button text
            text = f"{status_emoji} {doc.filename}\n{doc.memory_count} memories, {doc.entity_count} entities"

            # Container frame for checkbox + button
            item_frame = ctk.CTkFrame(self, fg_color="transparent")
            item_frame.pack(fill="x", pady=2)

            # Checkbox for multi-select
            checkbox = ctk.CTkCheckBox(
                item_frame,
                text="",
                width=30,
                checkbox_width=20,
                checkbox_height=20
            )
            checkbox.pack(side="left", padx=(5, 0))

            # Button for viewing details
            btn = ctk.CTkButton(
                item_frame,
                text=text,
                anchor="w",
                font=ctk.CTkFont(size=13),
                height=50,
                command=lambda d=doc.doc_id: self._select_document(d)
            )
            btn.pack(side="left", fill="x", expand=True, padx=(5, 0))

            self.doc_items.append((item_frame, btn, checkbox, doc.doc_id))

    def _select_document(self, doc_id: str):
        """Handle document selection for viewing details."""
        self.selected_doc_id = doc_id
        self.on_select_callback(doc_id)

        # Visual feedback - highlight selected with blue color
        for item_frame, btn, checkbox, item_doc_id in self.doc_items:
            if item_doc_id == doc_id:
                btn.configure(fg_color=("#3b82f6", "#2563eb"))  # Blue highlight
            else:
                btn.configure(fg_color=("gray75", "gray25"))  # Default gray

    def get_selected_for_deletion(self) -> List[str]:
        """Get list of doc_ids that are checked for deletion."""
        selected = []
        for item_frame, btn, checkbox, doc_id in self.doc_items:
            if checkbox.get():  # Checkbox is checked
                selected.append(doc_id)
        return selected

    def select_all(self):
        """Check all checkboxes."""
        for item_frame, btn, checkbox, doc_id in self.doc_items:
            checkbox.select()

    def clear_selections(self):
        """Uncheck all checkboxes."""
        for item_frame, btn, checkbox, doc_id in self.doc_items:
            checkbox.deselect()


class DocumentDetails(ctk.CTkFrame):
    """Document details panel with tabs."""

    def __init__(self, parent):
        super().__init__(parent)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create tabview
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Add tabs
        self.tabs.add("Content")
        self.tabs.add("Memories")
        self.tabs.add("Entities")
        self.tabs.add("Metadata")

        # Content tab
        self.content_text = ctk.CTkTextbox(
            self.tabs.tab("Content"),
            wrap="word",
            font=ctk.CTkFont(family="Courier", size=12)
        )
        self.content_text.pack(fill="both", expand=True, padx=10, pady=10)

        # Memories tab
        self.memories_text = ctk.CTkTextbox(
            self.tabs.tab("Memories"),
            wrap="word",
            font=ctk.CTkFont(size=12)
        )
        self.memories_text.pack(fill="both", expand=True, padx=10, pady=10)

        # Entities tab
        self.entities_text = ctk.CTkTextbox(
            self.tabs.tab("Entities"),
            wrap="word",
            font=ctk.CTkFont(size=12)
        )
        self.entities_text.pack(fill="both", expand=True, padx=10, pady=10)

        # Metadata tab
        self.metadata_text = ctk.CTkTextbox(
            self.tabs.tab("Metadata"),
            wrap="word",
            font=ctk.CTkFont(family="Courier", size=12)
        )
        self.metadata_text.pack(fill="both", expand=True, padx=10, pady=10)

        self.clear()

    def display_document(self, doc: DocumentInfo, manager: DocumentManager):
        """Display document details in all tabs."""
        # Content tab
        self.content_text.configure(state="normal")
        self.content_text.delete("1.0", "end")
        self.content_text.insert("1.0", doc.content_preview)
        self.content_text.configure(state="disabled")

        # Memories tab
        memories = manager.get_document_memories(doc.doc_id, doc.filename)
        self.memories_text.configure(state="normal")
        self.memories_text.delete("1.0", "end")

        if memories:
            for i, mem in enumerate(memories, 1):
                tier = mem.get('tier', 'unknown')
                importance = mem.get('importance', 0.0)
                text = mem.get('text', mem.get('content', 'No content'))[:200]

                self.memories_text.insert("end", f"[{i}] Tier: {tier} | Importance: {importance:.2f}\n")
                self.memories_text.insert("end", f"{text}...\n\n")
        else:
            self.memories_text.insert("1.0", "No memories found for this document.")

        self.memories_text.configure(state="disabled")

        # Entities tab
        self.entities_text.configure(state="normal")
        self.entities_text.delete("1.0", "end")

        if doc.entity_names:
            for entity in doc.entity_names:
                self.entities_text.insert("end", f"• {entity}\n")
        else:
            self.entities_text.insert("1.0", "No entities found in this document.")

        self.entities_text.configure(state="disabled")

        # Metadata tab
        self.metadata_text.configure(state="normal")
        self.metadata_text.delete("1.0", "end")

        metadata = f"""Filename: {doc.filename}
File Type: {doc.file_type}
File Size: {doc.file_size:,} bytes
Import Date: {doc.import_date}
Import Status: {doc.import_status}

Chunks Processed: {doc.chunk_count}
Memories Extracted: {doc.memory_count}
Entities Mentioned: {doc.entity_count}

Document ID: {doc.doc_id}
"""

        if doc.error_log:
            metadata += f"\nErrors:\n{doc.error_log}"

        self.metadata_text.insert("1.0", metadata)
        self.metadata_text.configure(state="disabled")

    def clear(self):
        """Clear all tabs."""
        for text_widget in [self.content_text, self.memories_text, self.entities_text, self.metadata_text]:
            text_widget.configure(state="normal")
            text_widget.delete("1.0", "end")
            text_widget.insert("1.0", "Select a document to view details...")
            text_widget.configure(state="disabled")


class DeleteConfirmationDialog(ctk.CTkToplevel):
    """Confirmation dialog for document deletion (supports single or multiple documents)."""

    def __init__(self, parent, documents: List[DocumentInfo]):
        super().__init__(parent)

        # Support both single document and list
        if isinstance(documents, list):
            self.documents = documents
        else:
            self.documents = [documents]

        self.is_multi = len(self.documents) > 1

        # Set title and size based on count
        if self.is_multi:
            self.title(f"Delete {len(self.documents)} Documents?")
            self.geometry("500x550")  # Increased height to ensure buttons always visible
        else:
            self.title("Delete Document?")
            self.geometry("500x350")

        self.resizable(False, False)

        self.result = None

        self._build_ui()

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        """Build dialog UI for single or multiple document deletion."""
        # Warning label
        warning_text = "⚠️ Delete Documents?" if self.is_multi else "⚠️ Delete Document?"
        warning_label = ctk.CTkLabel(
            self,
            text=warning_text,
            font=ctk.CTkFont(size=20, weight="bold")
        )
        warning_label.pack(pady=(20, 10))

        # Document list
        if self.is_multi:
            # Info label
            info_label = ctk.CTkLabel(
                self,
                text=f"Delete these {len(self.documents)} documents?",
                font=ctk.CTkFont(size=13)
            )
            info_label.pack(pady=5)

            # Use CTkTextbox with FIXED HEIGHT (more reliable than ScrollableFrame)
            docs_textbox = ctk.CTkTextbox(
                self,
                height=180,  # Fixed height - will not expand
                width=450,
                wrap="word",
                font=ctk.CTkFont(size=12)
            )
            docs_textbox.pack(pady=10, padx=20)

            # Populate document list
            for doc in self.documents:
                docs_textbox.insert("end", f"• {doc.filename}\n")

            # Make read-only
            docs_textbox.configure(state="disabled")
        else:
            # Single document
            info_label = ctk.CTkLabel(
                self,
                text=f'Delete "{self.documents[0].filename}"?',
                font=ctk.CTkFont(size=14)
            )
            info_label.pack(pady=5)

        # Calculate total impact
        total_memories = sum(doc.memory_count for doc in self.documents)
        total_entities = sum(doc.entity_count for doc in self.documents)

        # Impact summary (compact version)
        impact_text = f"{total_memories} memories, {total_entities} entities"
        if self.is_multi:
            impact_text = f"{len(self.documents)} docs: {impact_text}"

        impact_label = ctk.CTkLabel(
            self,
            text=f"Will remove: {impact_text}",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        impact_label.pack(pady=5)

        # Option: Keep memories
        self.keep_memories_var = ctk.BooleanVar(value=False)
        checkbox_text = "Keep memories" if not self.is_multi else f"Keep memories from all {len(self.documents)} docs"
        self.keep_memories_check = ctk.CTkCheckBox(
            self,
            text=checkbox_text,
            variable=self.keep_memories_var,
            font=ctk.CTkFont(size=12)
        )
        self.keep_memories_check.pack(pady=5)

        # Spacer to push buttons to bottom
        spacer = ctk.CTkFrame(self, fg_color="transparent", height=20)
        spacer.pack(fill="both", expand=True)

        # Buttons frame - always at bottom
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(side="bottom", pady=20, fill="x")

        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._cancel,
            width=120,
            font=ctk.CTkFont(size=14)
        )
        cancel_btn.pack(side="left", padx=10)

        delete_btn = ctk.CTkButton(
            button_frame,
            text="Delete All" if self.is_multi else "Delete",
            command=self._delete,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            width=120,
            font=ctk.CTkFont(size=14)
        )
        delete_btn.pack(side="left", padx=10)

    def _cancel(self):
        """Cancel deletion."""
        self.result = None
        self.destroy()

    def _delete(self):
        """Confirm deletion."""
        if self.keep_memories_var.get():
            self.result = "delete_doc_only"
        else:
            self.result = "delete_all"
        self.destroy()

    def show(self):
        """Show dialog and return result."""
        self.wait_window()
        return self.result
