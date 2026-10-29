import { permanentRedirect } from "next/navigation";

// Keep existing bookmarks useful after retiring the recorded-example player.
export default function RetiredReplayPage() {
  permanentRedirect("/lab");
}
