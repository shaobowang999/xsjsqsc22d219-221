import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main


class VideoParameterTests(unittest.IsolatedAsyncioTestCase):
    async def submit(self, *, apimart=False, **parameters):
        submitted = []

        def upstream(request):
            import json
            submitted.append(json.loads(request.content))
            return httpx.Response(200, json={"video_url": "https://example.invalid/result.mp4"})

        client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
        provider = {"id": "test", "name": "Test", "base_url": "https://example.invalid", "video_models": []}
        payload = main.CanvasVideoRequest(prompt="A moving landscape", provider_id="test", **parameters)
        with (
            patch.object(main, "get_api_provider", return_value=provider),
            patch.object(main, "provider_env_key_value", return_value="test-key"),
            patch.object(main, "is_apimart_provider", return_value=apimart),
            patch.object(main.httpx, "AsyncClient", return_value=client),
            patch.object(main, "reference_to_data_url", return_value="data:image/png;base64,aW1hZ2U="),
            patch.object(main, "save_remote_video_to_output", new=AsyncMock(return_value="/output/test.mp4")),
        ):
            result = await main.canvas_video(payload)
        self.assertEqual(result["videos"], ["/output/test.mp4"])
        self.assertEqual(len(submitted), 1)
        return submitted[0], payload

    async def test_flux_legacy_resolutions_reach_upstream_as_quality_names(self):
        for value, expected in [("480p", "hd"), ("720p", "hd"), ("780P", "hd"), ("1080p", "fhd"), ("HD", "hd"), ("fhd", "fhd"), ("", "hd"), ("auto", "hd")]:
            with self.subTest(resolution=value):
                body, original = await self.submit(model="flux-3-video", resolution=value)
                self.assertEqual(body["resolution"], expected)
                self.assertEqual(original.resolution, value)

    async def test_flux_apimart_path_also_normalizes_resolution(self):
        body, _ = await self.submit(model="flux-3-video", resolution="480p", apimart=True)
        self.assertEqual(body["resolution"], "hd")

    async def test_generic_auto_ratio_is_explicit_in_both_fields(self):
        for value in ["auto", " AUTO ", "", "adaptive", "keep_ratio"]:
            with self.subTest(ratio=value):
                body, _ = await self.submit(model="flux-3-video", aspect_ratio=value, resolution="480p")
                self.assertEqual(body["aspect_ratio"], "16:9")
                self.assertEqual(body["ratio"], "16:9")
                self.assertEqual(body["size"], "16:9")

    async def test_generic_size_alias_never_defaults_to_auto(self):
        for size in ["", "auto", "keep_ratio", "adaptive"]:
            with self.subTest(size=size):
                body, _ = await self.submit(model="other-model", aspect_ratio="9:16", size=size)
                self.assertEqual(body["size"], "9:16")
        body, _ = await self.submit(model="other-model", aspect_ratio="9:16", size="720x1280")
        self.assertEqual(body["size"], "720x1280")

    async def test_explicit_ratio_and_other_model_resolution_are_preserved(self):
        body, _ = await self.submit(model="other-video-model", aspect_ratio="9:16", resolution="480p")
        self.assertEqual(body["aspect_ratio"], "9:16")
        self.assertEqual(body["ratio"], "9:16")
        self.assertEqual(body["resolution"], "480p")

    async def test_image_to_video_keeps_reference_and_normalizes_parameters(self):
        body, _ = await self.submit(model="flux-3-video", aspect_ratio="auto", resolution="1080p", images=[{"url": "/assets/input/test.png"}])
        self.assertEqual(body["resolution"], "fhd")
        self.assertEqual(body["aspect_ratio"], "16:9")
        self.assertEqual(body["images"], ["data:image/png;base64,aW1hZ2U="])

    async def test_native_provider_keeps_its_own_auto_ratio(self):
        payload = main.CanvasVideoRequest(prompt="A landscape", aspect_ratio="auto", provider_id="native")
        generate = AsyncMock(return_value={"videos": ["/output/native.mp4"]})
        with patch.object(main, "get_api_provider", return_value={"id": "native"}), patch.object(main, "is_jimeng_provider", return_value=True), patch.object(main, "generate_jimeng_video", new=generate):
            await main.canvas_video(payload)
        self.assertEqual(generate.call_args.args[0].aspect_ratio, "auto")

    async def test_unsupported_flux_resolution_is_rejected_before_api_call(self):
        with patch.object(main.httpx, "AsyncClient") as client:
            with self.assertRaises(main.HTTPException) as caught:
                await main.canvas_video(main.CanvasVideoRequest(prompt="A landscape", model="flux-3-video", resolution="4k"))
        self.assertEqual(caught.exception.status_code, 400)
        client.assert_not_called()

    def test_flux_detection_handles_variants_without_matching_other_models(self):
        for model in ["flux-3-video", "FLUX-3-VIDEO", "provider/flux-3-video-fast"]:
            self.assertTrue(main.is_flux3_video_model(model))
        for model in ["flux-3-image", "flux-3-videoish", "veo3-fast"]:
            self.assertFalse(main.is_flux3_video_model(model))


if __name__ == "__main__":
    unittest.main()
