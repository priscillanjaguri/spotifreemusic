import { Capacitor } from "@capacitor/core";
import { FilePicker } from "@capawesome/capacitor-file-picker";

/** MIME types Android's document picker understands for library audio. */
const AUDIO_TYPES = [
  "audio/*",
  "audio/mpeg",
  "audio/mp4",
  "audio/x-m4a",
  "audio/aac",
  "audio/flac",
  "audio/ogg",
  "audio/wav",
  "audio/x-wav",
  "audio/x-flac",
];

function isCancel(err: unknown): boolean {
  const msg = err instanceof Error ? err.message : String(err ?? "");
  return /cancel|dismiss|user.?cancel/i.test(msg);
}

/**
 * Turn a native picked path into a browser `File` for XHR upload.
 * Prefer `webPath` / `convertFileSrc` + fetch (avoids base64 OOM on large tracks).
 */
async function pickedToFile(picked: {
  name: string;
  mimeType: string;
  path?: string;
  webPath?: string;
  blob?: Blob;
}): Promise<File> {
  if (picked.blob) {
    return new File([picked.blob], picked.name, {
      type: picked.mimeType || picked.blob.type || "application/octet-stream",
    });
  }

  const src =
    picked.webPath ||
    (picked.path ? Capacitor.convertFileSrc(picked.path) : "");
  if (!src) throw new Error(`No readable path for ${picked.name}`);

  const res = await fetch(src);
  if (!res.ok) throw new Error(`Couldn't read ${picked.name}`);
  const blob = await res.blob();
  return new File([blob], picked.name, {
    type: picked.mimeType || blob.type || "application/octet-stream",
  });
}

/**
 * Open the native audio file picker on Capacitor (Android/iOS).
 * Returns `null` if the user cancels. Falls back to `null` on web so the
 * caller can use a plain `<input type="file">`.
 */
export async function pickLibraryAudioFiles(): Promise<File[] | null> {
  if (!Capacitor.isNativePlatform()) return null;

  try {
    // Best-effort; SAF often works without this, but MediaStore audio needs it.
    try {
      await FilePicker.requestPermissions({ permissions: ["readExternalStorage"] });
    } catch {
      /* ignore — picker may still work via system document UI */
    }

    const { files } = await FilePicker.pickFiles({
      types: AUDIO_TYPES,
      limit: 0,
      readData: false,
    });
    if (!files.length) return [];

    const out: File[] = [];
    for (const f of files) {
      out.push(await pickedToFile(f));
    }
    return out;
  } catch (err) {
    if (isCancel(err)) return [];
    throw err;
  }
}

export function isNativeLibraryPicker(): boolean {
  return Capacitor.isNativePlatform();
}
