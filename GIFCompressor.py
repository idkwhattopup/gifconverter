import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk, messagebox
from PIL import Image, ImageSequence, ImageTk
import os
from pathlib import Path
import threading
import json
import tempfile
import itertools

GIF_FILE_TYPES = [("GIF files", "*.gif")]
NO_PREVIEW_TEXT = "No preview available"
MAX_SIZE_ERROR = "Error: Max size must be between 0.1 and 100 MB"
KEY_MAX_SIZE_MB = "max_size_mb"
TAG_ALL = "all"
TEXT_BROWSE = "Browse"
EVENT_ENTER = "<Enter>"
EVENT_LEAVE = "<Leave>"


class GIFCompressorApp:
    """A Tkinter-based application for compressing GIFs to a specified size."""

    def __init__(self, master):
        """Initialize the GUI and application state."""
        self.root = master
        self.root.title("GIF Compressor")
        self.root.minsize(600, 600)

        self.root.resizable(True, True)

        self.is_compressing = False
        self.home_dir = str(Path.home())
        self.input_path = tk.StringVar(
            value=str(Path(self.home_dir) / "compressed_output_final.gif")
        )
        self.output_path = tk.StringVar(
            value=str(Path(self.home_dir) / "output_compressed.gif")
        )
        self.max_size_mb = tk.StringVar(value="4")
        self.preview_image = None

        self.settings_file = Path(self.home_dir) / ".gif_compressor_settings.json"

        tk.Label(root, text="Input GIF:").grid(
            row=0, column=0, padx=5, pady=5, sticky="e"
        )
        input_entry = tk.Entry(root, textvariable=self.input_path, width=50)
        input_entry.grid(row=0, column=1, padx=5, pady=5)
        input_entry.bind(
            EVENT_ENTER,
            lambda e: self.show_tooltip(input_entry, "Select the input GIF file"),
        )
        input_entry.bind(EVENT_LEAVE, lambda e: self.hide_tooltip())
        tk.Button(root, text=TEXT_BROWSE, command=self.browse_input).grid(
            row=0, column=2, padx=5, pady=5
        )

        tk.Label(root, text="Output GIF:").grid(
            row=1, column=0, padx=5, pady=5, sticky="e"
        )
        output_entry = tk.Entry(root, textvariable=self.output_path, width=50)
        output_entry.grid(row=1, column=1, padx=5, pady=5)
        output_entry.bind(
            EVENT_ENTER,
            lambda e: self.show_tooltip(
                output_entry, "Select where to save the compressed GIF"
            ),
        )
        output_entry.bind(EVENT_LEAVE, lambda e: self.hide_tooltip())
        tk.Button(root, text=TEXT_BROWSE, command=self.browse_output).grid(
            row=1, column=2, padx=5, pady=5
        )

        tk.Label(root, text="Max Size (MB):").grid(
            row=2, column=0, padx=5, pady=5, sticky="e"
        )
        size_entry = tk.Entry(root, textvariable=self.max_size_mb, width=10)
        size_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        size_entry.bind(
            EVENT_ENTER,
            lambda e: self.show_tooltip(
                size_entry, "Enter target size in MB (0.1 to 100)"
            ),
        )
        size_entry.bind(EVENT_LEAVE, lambda e: self.hide_tooltip())

        self.compress_button = tk.Button(
            root, text="Compress GIF", command=self.start_compression
        )
        self.compress_button.grid(row=3, column=0, pady=10, sticky="e")
        self.cancel_button = tk.Button(
            root, text="Cancel", command=self.cancel_compression, state="disabled"
        )
        self.cancel_button.grid(row=3, column=1, pady=10, sticky="w")
        tk.Button(root, text="Save Settings", command=self.save_settings).grid(
            row=3, column=2, pady=10, sticky="w"
        )

        self.progress_label = tk.Label(root, text="Ready")
        self.progress_label.grid(row=4, column=0, columnspan=3, padx=5, pady=2)
        self.progress = ttk.Progressbar(
            root, orient="horizontal", length=400, mode="determinate"
        )
        self.progress.grid(row=5, column=0, columnspan=3, padx=5, pady=5)

        tk.Label(root, text="Preview:").grid(
            row=6, column=0, padx=5, pady=5, sticky="e"
        )
        self.preview_canvas = tk.Canvas(
            root, width=200, height=200, bg="white", highlightthickness=1
        )
        self.preview_canvas.grid(row=6, column=1, columnspan=2, padx=5, pady=5)
        self.preview_label = tk.Label(root, text=NO_PREVIEW_TEXT)
        self.preview_label.grid(row=7, column=0, columnspan=3, padx=5, pady=2)

        self.status_text = scrolledtext.ScrolledText(
            root, width=60, height=10, wrap=tk.WORD
        )
        self.status_text.grid(row=8, column=0, columnspan=3, padx=5, pady=5)

        self.tooltip = None

        self.load_settings()

    def show_tooltip(self, widget, text):
        """Show a tooltip window near the specified widget."""
        if self.tooltip:
            self.hide_tooltip()

        x = widget.winfo_rootx() + 20
        y = widget.winfo_rooty() + widget.winfo_height() + 5

        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1
        )
        label.pack()

    def hide_tooltip(self):
        """Hide the tooltip if it exists."""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    def browse_input(self):
        """Open file dialog to select input GIF."""
        file_path = filedialog.askopenfilename(filetypes=GIF_FILE_TYPES)
        if file_path:
            self.input_path.set(file_path)

    def browse_output(self):
        """Opens a file dialog to select the output GIF path."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".gif", filetypes=GIF_FILE_TYPES
        )
        if file_path:
            self.output_path.set(file_path)

    def save_settings(self):
        """Save max size to a JSON file."""
        try:
            max_size = float(self.max_size_mb.get())
            if 0.1 <= max_size <= 100:
                settings = {KEY_MAX_SIZE_MB: max_size}
                with open(self.settings_file, "w") as f:
                    json.dump(settings, f)
                self.log("Settings saved successfully")
            else:
                self.log(MAX_SIZE_ERROR)
        except ValueError:
            self.log("Error: Invalid max size value for saving settings")
        except Exception as e:
            self.log(f"Error saving settings: {str(e)}")

    def load_settings(self):
        """Load max size from a JSON file if it exists."""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, "r") as f:
                    settings = json.load(f)
                    max_size = settings.get(KEY_MAX_SIZE_MB, 4)
                    if 0.1 <= max_size <= 100:
                        self.max_size_mb.set(str(max_size))
                        self.log("Loaded saved settings")
                    else:
                        self.log("Invalid max size in settings file, using default")
        except Exception as e:
            self.log(f"Error loading settings: {str(e)}")

    def cancel_compression(self):
        """Set a flag to stop compression."""
        self.is_compressing = False
        self.compress_button.config(state="normal")
        self.cancel_button.config(state="disabled")
        self.progress["value"] = 0
        self.progress_label.config(text="Compression cancelled")
        self.log("Compression cancelled by user")

    def log(self, message):
        """Display a message in the log box."""
        if hasattr(self, "status_text"):
            self.status_text.insert(tk.END, message + "\n")
            self.status_text.see(tk.END)
            self.root.update_idletasks()
        else:
            print(f"[Log pre-init]: {message}")

    def start_compression(self):
        """Start compression in a separate thread."""
        if self.is_compressing:
            return
        self.is_compressing = True
        self.compress_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        self.progress["value"] = 0
        self.progress_label.config(text="Starting compression...")
        self.preview_canvas.delete(TAG_ALL)
        self.preview_label.config(text=NO_PREVIEW_TEXT)

        compression_thread = threading.Thread(target=self.compress_gif)
        compression_thread.daemon = True
        compression_thread.start()

    def update_preview(self, frame):
        """Display a single frame as a preview."""
        try:

            frame = frame.copy()
            frame.thumbnail((200, 200), Image.Resampling.LANCZOS)
            self.preview_image = ImageTk.PhotoImage(frame)
            self.preview_canvas.delete(TAG_ALL)
            self.preview_canvas.create_image(100, 100, image=self.preview_image)
            self.preview_label.config(text="Preview of compressed GIF (first frame)")
        except Exception as e:
            self.log(f"Error displaying preview: {str(e)}")

    def try_compression_settings(
        self, frames, skip_frames, colors, resize_ratio, duration, output_path
    ):
        """Try compressing with given settings."""
        if not self.is_compressing:
            raise InterruptedError("Compression cancelled")

        self.progress_label.config(
            text=f"Trying: {resize_ratio * 100:.0f}% resize, skip_frames={skip_frames}, {colors} colors"
        )
        self.root.update_idletasks()

        if skip_frames:
            frames = frames[::2]
            self.log(f"After skipping frames: {len(frames)} frames")

        optimized_frames = []
        for frame in frames:
            if frame.mode == "RGBA":
                frame = frame.convert("RGB")
            quantized_frame = frame.quantize(colors=colors, method=2)
            optimized_frames.append(quantized_frame)
        self.log(f"Optimized with {colors} colors")

        # Create a secure temporary file path in the output directory
        temp_dir = os.path.dirname(output_path) or "."
        fd, temp_path = tempfile.mkstemp(
            prefix="gifcompress_", suffix=".gif", dir=temp_dir
        )
        os.close(fd)  # Close the OS handle before PIL writes to the path on Windows
        optimized_frames[0].save(
            temp_path,
            save_all=True,
            append_images=optimized_frames[1:],
            duration=duration * 1000,
            loop=0,
            optimize=True,
            subrectangles=True,
            dither=0,
        )

        if os.path.exists(temp_path):
            output_size = os.path.getsize(temp_path)
            self.log(f"Output size: {output_size / (1024 * 1024):.2f}MB")
            return output_size, optimized_frames, temp_path
        raise FileNotFoundError(f"Failed to create temporary GIF: {temp_path}")

    def get_cached_frames(self, resize_ratio, original_frames, frame_cache):
        """Get or create resized frames."""
        if resize_ratio in frame_cache:
            return frame_cache[resize_ratio]

        if resize_ratio < 1.0:
            frames = [
                frame.resize(
                    (int(frame.width * resize_ratio), int(frame.height * resize_ratio)),
                    Image.Resampling.LANCZOS,
                )
                for frame in original_frames
            ]
            self.log(f"Resized frames to {resize_ratio * 100:.1f}% of original size")
            frame_cache[resize_ratio] = frames
        else:
            frame_cache[resize_ratio] = original_frames

        return frame_cache[resize_ratio]

    def process_compression_step(
        self,
        params,
        frames,
        duration,
        output_path,
        target_size,
        tolerance,
        successful_combinations,
    ):
        """Process a single compression setting combination."""
        skip_frames, colors, resize_ratio = params

        try:
            size, optimized_frames, temp_path = self.try_compression_settings(
                frames,
                skip_frames,
                colors,
                resize_ratio,
                duration,
                output_path,
            )

            if size <= target_size:
                successful_combinations.append(
                    (
                        size,
                        optimized_frames,
                        resize_ratio,
                        skip_frames,
                        colors,
                        temp_path,
                    )
                )

                if target_size - tolerance <= size:
                    return True

            else:

                try:
                    os.remove(temp_path)
                except OSError:
                    pass

        except (OSError, ValueError, RuntimeError):
            pass

        return False

    def find_best_compression_combination(
        self, original_frames, duration, max_size_mb, output_path
    ):
        """Iterate through compression strategies to find the best combination."""
        resize_ratios = [1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5]
        colors_options = [256, 128, 64]
        skip_frames_options = [False, True]
        target_size = max_size_mb * 1024 * 1024
        tolerance = 0.05 * target_size
        successful_combinations = []

        total_iterations = (
            len(resize_ratios) * len(skip_frames_options) * len(colors_options)
        )
        current_iteration = 0
        frame_cache = {}

        for resize_ratio in resize_ratios:
            if not self.is_compressing:
                break

            self.log(f"Processing resize_ratio={resize_ratio * 100:.1f}%")
            frames = self.get_cached_frames(resize_ratio, original_frames, frame_cache)

            for skip_frames, colors in itertools.product(
                skip_frames_options, colors_options
            ):
                if not self.is_compressing:
                    break

                current_iteration += 1
                self.progress["value"] = (current_iteration / total_iterations) * 100

                params = (skip_frames, colors, resize_ratio)
                found_optimal = self.process_compression_step(
                    params,
                    frames,
                    duration,
                    output_path,
                    target_size,
                    tolerance,
                    successful_combinations,
                )

                if found_optimal:
                    return successful_combinations

        return successful_combinations

    def get_validated_max_size(self):
        """Validate and return max size in MB."""
        try:
            max_size_mb = float(self.max_size_mb.get())
            if 0.1 <= max_size_mb <= 100:
                return max_size_mb
            self.log(MAX_SIZE_ERROR)
        except ValueError:
            self.log("Error: Invalid max size value. Please enter a number")
        return None

    def validate_input_file(self, input_path):
        """Check if the input file exists and is not too large."""
        if not os.path.isfile(input_path):
            self.log("Error: Input GIF not found")
            return False

        try:
            file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
            if file_size_mb > 100 and not messagebox.askyesno(
                "Large File Warning",
                f"Input GIF is {file_size_mb:.1f}MB. Compression may be slow or fail. Continue?",
            ):
                self.log("Compression cancelled due to large file size")
                return False
        except Exception as e:
            self.log(f"Error checking file size: {str(e)}")
            return False
        return True

    def validate_gif_content(self, input_path):
        """Verify GIF is animated and check frame count."""
        try:
            with Image.open(input_path) as gif:
                if not getattr(gif, "is_animated", False):
                    self.log("Error: Input file is not an animated GIF")
                    return False
                if gif.n_frames < 1:
                    self.log("Error: Input GIF contains no frames")
                    return False
                if gif.n_frames > 1000 and not messagebox.askyesno(
                    "High Frame Count Warning",
                    f"Input GIF has {gif.n_frames} frames. Compression may be slow. Continue?",
                ):
                    self.log("Compression cancelled due to high frame count")
                    return False
        except Exception as e:
            self.log(f"Error: Invalid GIF file: {str(e)}")
            return False
        return True

    def ensure_output_directory(self, output_path):
        """Ensure the output directory exists and is writable."""
        output_dir = os.path.dirname(output_path) or "."
        self.log(f"Output directory: {output_dir}")
        if not os.path.exists(output_dir):
            self.log(f"Creating output directory: {output_dir}")
            try:
                os.makedirs(output_dir)
            except Exception as e:
                self.log(f"Error: Could not create output directory: {str(e)}")
                return False

        try:
            test_file = os.path.join(output_dir, "test_write.tmp")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            self.log("Output directory is writable")
        except Exception as e:
            self.log(f"Error: Cannot write to output directory {output_dir}: {str(e)}")
            return False
        return True

    @staticmethod
    def cleanup_temp_files(combinations):
        """Remove all temporary files from the combinations list."""
        if not combinations:
            return
        for item in combinations:
            try:
                temp_path = item[5]
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except OSError:
                pass

    @staticmethod
    def score_combination(combination):
        """
        Score a compression combination to determine the 'best' one.

        The goal is to select the highest-quality GIF that still fits under the target size.
        Priority order (highest first):

        1. Largest file size (closer to target is better, but ≤ target)
        2. Highest resolution (largest resize_ratio)
        3. No frame skipping (False > True)
        4. More colors (higher palette size preserves quality better)

        Args:
            combination: Tuple of (size, frames, resize_ratio, skip_frames, colors, temp_path)

        Returns:
            Tuple of scoring criteria in descending order of importance.
            Higher values are preferred.
        """
        size, _, resize_ratio, skip_frames, colors, _ = combination
        return (
            size,  # Maximize size (but already ≤ target)
            resize_ratio,  # Prefer higher resolution
            not skip_frames,  # Prefer keeping all frames (True if not skipped)
            colors,  # Prefer richer palette
        )

    def save_best_result(self, successful_combinations, output_path, duration):
        """Save the best compression result."""
        if not successful_combinations:
            self.log("No valid compressed versions met the size requirement.")
            return

        # Find the combination with the highest score according to our criteria
        best_combination = max(
            successful_combinations, key=GIFCompressorApp.score_combination
        )

        (
            _,
            best_frames,
            best_resize_ratio,
            best_skip_frames,
            best_colors,
            temp_path,
        ) = best_combination
        self.log(
            f"Saving final GIF with settings: resize_ratio={best_resize_ratio * 100:.1f}%, "
            f"skip_frames={best_skip_frames}, colors={best_colors}"
        )

        try:
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            os.rename(temp_path, output_path)
        except OSError as e:
            self.log(f"Could not rename temp file: {e}. Falling back to direct save.")
            best_frames[0].save(
                output_path,
                save_all=True,
                append_images=best_frames[1:],
                duration=duration * 1000,
                loop=0,
                optimize=True,
                subrectangles=True,
                dither=0,
            )

        self.cleanup_temp_files(successful_combinations)

        final_size = os.path.getsize(output_path)
        self.log(f"Success! Output GIF size: {final_size / (1024 * 1024):.2f}MB")

        self.root.after(0, self.update_preview, best_frames[0])

    def compress_gif(self):
        """Compress the input GIF to meet the target size."""
        input_path = self.input_path.get()
        output_path = self.output_path.get()
        successful_combinations = []

        max_size_mb = self.get_validated_max_size()
        if max_size_mb is None:
            self.reset_ui()
            return

        self.status_text.delete(1.0, tk.END)
        self.log(f"Input path: {input_path}")
        self.log(f"Output path: {output_path}")
        self.log(f"Target max size: {max_size_mb}MB")

        if not self.validate_input_file(input_path):
            self.reset_ui()
            return

        if not self.validate_gif_content(input_path):
            self.reset_ui()
            return

        if not self.ensure_output_directory(output_path):
            self.reset_ui()
            return

        try:
            gif = Image.open(input_path)
            original_frames = [frame.copy() for frame in ImageSequence.Iterator(gif)]
            frame_count = len(original_frames)
            self.log(f"Original frame count: {frame_count}")

            duration = gif.info.get("duration", 100) / 1000.0
            self.log(f"Frame duration: {duration} seconds")

            successful_combinations = self.find_best_compression_combination(
                original_frames, duration, max_size_mb, output_path
            )

            if not self.is_compressing:
                self.cleanup_temp_files(successful_combinations)
                self.reset_ui()
                return

            if successful_combinations:
                self.save_best_result(successful_combinations, output_path, duration)
            else:
                self.log(f"Warning: Could not reduce size below {max_size_mb}MB")

                self.log("No combinations were successful under the target size.")

            self.reset_ui(success=True)

        except InterruptedError:
            self.cleanup_temp_files(successful_combinations)
            self.reset_ui()
        except Exception as e:
            self.log(f"Error processing GIF: {str(e)}")
            self.cleanup_temp_files(successful_combinations)
            self.reset_ui()

    def reset_ui(self, success=False):
        """Reset the UI state after compression."""
        self.is_compressing = False
        self.compress_button.config(state="normal")
        self.cancel_button.config(state="disabled")

        if success:
            self.progress["value"] = 100
            self.progress_label.config(text="Compression Complete")
        else:
            self.progress["value"] = 0
            self.progress_label.config(text="Ready")


def _test_scoring_logic():
    """Test that score_combination selects the expected best combination."""
    # Sample successful combinations: (size_bytes, frames, resize_ratio, skip_frames, colors, temp_path)
    combos = [
        (3_800_000, None, 0.8, True, 128, "a.gif"),  # smaller size, skipped frames
        (3_900_000, None, 0.8, False, 128, "b.gif"),  # larger size, no skip
        (3_850_000, None, 0.9, True, 256, "c.gif"),  # higher res, but skipped
        (3_870_000, None, 0.8, False, 256, "d.gif"),  # good size, no skip, max colors
        (
            3_950_000,
            None,
            0.9,
            False,
            256,
            "e.gif",
        ),  # the largest size, highest res, no skip, max colors
    ]

    best = max(combos, key=GIFCompressorApp.score_combination)
    assert (
        best == combos[4]
    ), "Scoring failed: expected highest res + no skip + max colors + largest size to win"

    print("✓ Scoring logic test passed: best combination selected correctly.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        _test_scoring_logic()
    else:
        root = tk.Tk()
        app = GIFCompressorApp(root)
        root.mainloop()
