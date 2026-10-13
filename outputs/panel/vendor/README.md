# OpenCut-AI subtitle serializers

Source: [Ekaanth/OpenCut-AI](https://github.com/Ekaanth/OpenCut-AI), pinned commit `eb8aef9f971648980673b207fc28eb76955883b3`.

`opencut_subtitles.py` preserves the original `services/ai-backend/app/services/subtitle_service.py` without modification. [MIT license](OpenCut-AI-LICENSE.txt) is retained. No full application or external service is installed.

The local wrapper `captions.py` retimes segments/words around reviewed cuts, quantizes timestamps and neutralizes ASS control text. FFmpeg/libass handles Persian rendering using DejaVu Sans in the Docker image.
