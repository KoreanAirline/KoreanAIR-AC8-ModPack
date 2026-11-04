# Building the current candidate

Use 64-bit Windows, Python 3.9+ and the .NET Framework 4.x C# compiler.
`python build_pack.py --launcher-only` compiles the managed launcher source.
`python build_pack.py --payload-zip Payload.zip` rebuilds Setup using the exact
redistributable payload supplied here. Keep the resulting Payload.zip beside
Setup. It contains mod components, never the game executable or a stock DAT.

The source archive contains reviewed campaign dialogue as key/en/ko JSON and
gzip. Historical whole CP tables, raw game localization files and private
captures are deliberately omitted. Native component sources and licenses are
included. Native rebuilds require Visual Studio C++ tools; campaign ABI checks
read a separately installed game executable, which is not redistributed.

Validation source may require the owner's separately installed game or external
loader fixtures. Private captures and full stock localization fixtures are not
part of this archive. Public copies sanitize personal filesystem paths, so their
hashes differ from the private source-bound records; PUBLIC_SOURCE_SHA256.json
records the exact distributed copies.

See SECURITY_STATUS.txt for the unresolved Defender report. The packaging step
does not execute or extract the quarantined launcher and does not publish.
