"""
Progress tracking for G-code Database Manager
Provides progress bar utilities for long-running operations
"""

from tqdm import tqdm
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable
import time


class ConsoleProgressTracker:
    """Console-based progress tracker using tqdm"""

    def __init__(self, total: int, desc: str = "Processing", unit: str = "item"):
        """
        Initialize console progress tracker

        Args:
            total: Total number of items to process
            desc: Description shown before progress bar
            unit: Unit name for items being processed
        """
        self.pbar = tqdm(total=total, desc=desc, unit=unit)

    def update(self, n: int = 1, postfix: Optional[str] = None):
        """
        Update progress

        Args:
            n: Number of items completed
            postfix: Optional status text to show after progress bar
        """
        self.pbar.update(n)
        if postfix:
            self.pbar.set_postfix_str(postfix)

    def close(self):
        """Close the progress bar"""
        self.pbar.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class GUIProgressTracker:
    """GUI-based progress tracker using tkinter"""

    def __init__(self, parent: tk.Widget, title: str = "Processing"):
        """
        Initialize GUI progress tracker

        Args:
            parent: Parent tkinter widget
            title: Window title
        """
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry("500x200")
        self.window.transient(parent)
        self.window.grab_set()

        # Make window stay on top
        self.window.attributes('-topmost', True)

        # Title
        self.title_label = tk.Label(
            self.window,
            text=title,
            font=('Arial', 12, 'bold')
        )
        self.title_label.pack(pady=10)

        # Progress bar
        self.progress = ttk.Progressbar(
            self.window,
            mode='determinate',
            length=400
        )
        self.progress.pack(pady=10, padx=50)

        # Status label
        self.status_label = tk.Label(
            self.window,
            text="Starting...",
            font=('Arial', 9)
        )
        self.status_label.pack(pady=5)

        # Statistics label
        self.stats_label = tk.Label(
            self.window,
            text="",
            font=('Arial', 9),
            fg='gray'
        )
        self.stats_label.pack(pady=5)

        # Cancel button
        self.cancelled = False
        self.cancel_btn = tk.Button(
            self.window,
            text="Cancel",
            command=self._on_cancel,
            bg='#dc3545',
            fg='white'
        )
        self.cancel_btn.pack(pady=10)

        self.start_time = time.time()
        self.total = 0
        self.current = 0

    def _on_cancel(self):
        """Handle cancel button click"""
        self.cancelled = True
        self.window.destroy()

    def configure(self, total: int, current: int = 0):
        """
        Configure progress tracker

        Args:
            total: Total number of items
            current: Current progress
        """
        self.total = total
        self.current = current
        self.progress['maximum'] = total
        self.progress['value'] = current

    def update(self, n: int = 1, status: Optional[str] = None,
              stats: Optional[dict] = None):
        """
        Update progress

        Args:
            n: Number of items completed since last update
            status: Status message to display
            stats: Dictionary of statistics to display
        """
        if self.cancelled:
            return

        self.current += n
        self.progress['value'] = self.current

        # Update status
        if status:
            self.status_label.config(text=status)
        else:
            percent = (self.current / self.total * 100) if self.total > 0 else 0
            self.status_label.config(text=f"{self.current} / {self.total} ({percent:.1f}%)")

        # Update statistics
        if stats:
            stats_text = "  |  ".join(f"{k}: {v}" for k, v in stats.items())
            self.stats_label.config(text=stats_text)

        # Calculate ETA
        if self.current > 0:
            elapsed = time.time() - self.start_time
            rate = self.current / elapsed
            remaining = (self.total - self.current) / rate if rate > 0 else 0
            eta_text = f"Rate: {rate:.1f} items/sec  |  ETA: {remaining:.1f}s"
            self.stats_label.config(text=eta_text)

        self.window.update()

    def is_cancelled(self) -> bool:
        """Check if operation was cancelled"""
        return self.cancelled

    def close(self):
        """Close the progress window"""
        try:
            self.window.destroy()
        except:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class NestedProgressTracker:
    """Nested progress tracker for operations with sub-tasks"""

    def __init__(self, parent: tk.Widget, title: str = "Processing"):
        """
        Initialize nested progress tracker

        Args:
            parent: Parent tkinter widget
            title: Window title
        """
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry("600x250")
        self.window.transient(parent)
        self.window.grab_set()
        self.window.attributes('-topmost', True)

        # Title
        tk.Label(
            self.window,
            text=title,
            font=('Arial', 12, 'bold')
        ).pack(pady=10)

        # Overall progress frame
        overall_frame = tk.Frame(self.window)
        overall_frame.pack(fill=tk.X, padx=50, pady=10)

        tk.Label(overall_frame, text="Overall Progress:",
                font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        self.overall_pb = ttk.Progressbar(overall_frame, mode='determinate')
        self.overall_pb.pack(fill=tk.X, pady=5)
        self.overall_label = tk.Label(overall_frame, text="0 / 0",
                                     font=('Arial', 9))
        self.overall_label.pack(anchor=tk.W)

        # Current progress frame
        current_frame = tk.Frame(self.window)
        current_frame.pack(fill=tk.X, padx=50, pady=10)

        tk.Label(current_frame, text="Current Task:",
                font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        self.current_pb = ttk.Progressbar(current_frame, mode='determinate')
        self.current_pb.pack(fill=tk.X, pady=5)
        self.current_label = tk.Label(current_frame, text="",
                                      font=('Arial', 9))
        self.current_label.pack(anchor=tk.W)

        # Cancel button
        self.cancelled = False
        tk.Button(
            self.window,
            text="Cancel",
            command=self._on_cancel,
            bg='#dc3545',
            fg='white',
            padx=20
        ).pack(pady=10)

    def _on_cancel(self):
        """Handle cancel button click"""
        self.cancelled = True
        self.window.destroy()

    def update_overall(self, current: int, total: int, label: str = ""):
        """Update overall progress"""
        if self.cancelled:
            return

        self.overall_pb['maximum'] = total
        self.overall_pb['value'] = current
        text = f"{current} / {total}"
        if label:
            text += f" - {label}"
        self.overall_label.config(text=text)
        self.window.update()

    def update_current(self, current: int, total: int, label: str = ""):
        """Update current task progress"""
        if self.cancelled:
            return

        self.current_pb['maximum'] = total
        self.current_pb['value'] = current
        text = f"{current} / {total}"
        if label:
            text += f" - {label}"
        self.current_label.config(text=text)
        self.window.update()

    def is_cancelled(self) -> bool:
        """Check if operation was cancelled"""
        return self.cancelled

    def close(self):
        """Close the progress window"""
        try:
            self.window.destroy()
        except:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def create_simple_progress_dialog(parent: tk.Widget, title: str,
                                  message: str, indeterminate: bool = False):
    """
    Create a simple progress dialog for operations without known duration

    Args:
        parent: Parent widget
        title: Dialog title
        message: Message to display
        indeterminate: If True, show indeterminate progress

    Returns:
        Dialog window
    """
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.geometry("400x120")
    dialog.transient(parent)
    dialog.attributes('-topmost', True)

    tk.Label(dialog, text=message, font=('Arial', 10)).pack(pady=20)

    mode = 'indeterminate' if indeterminate else 'determinate'
    pb = ttk.Progressbar(dialog, mode=mode, length=300)
    pb.pack(pady=10)

    if indeterminate:
        pb.start(10)

    return dialog


if __name__ == "__main__":
    # Test the module
    print("Testing ConsoleProgressTracker...")
    with ConsoleProgressTracker(100, desc="Test Progress") as tracker:
        for i in range(100):
            time.sleep(0.01)
            tracker.update(1, f"Item {i+1}")

    print("\nConsole test complete!")
    print("Run with tkinter parent to test GUI trackers")
