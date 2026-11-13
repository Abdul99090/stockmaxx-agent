# Jawaban Form Submission — Base "Stocks Maxxing" Builder Quest

**Form resmi (dari tombol "Apply Now" di Quest Page):**
https://docs.google.com/forms/d/1zotYvkeAtDjR2MKk3qNxyNIAfJ_IPQtzTtjNhOAF8js/viewform

**CATATAN PENTING buat agen utama:** teks form yang terambil via fetch hanya menampilkan
header form (syarat singkat + privacy), label field satu-satu TIDAK ikut tertarik
(Google Form dinamis). Jadi di bawah ini jawaban disiapkan per topik yang diwajibkan
aturan resmi Bagian 5 (link post X, Track yang dimasuki, info lain yang diminta form) —
pas submit, cocokkan label field live-nya satu-satu. JANGAN submit dari file ini tanpa
membaca field aslinya.

Kondisi yang tertulis di header form (verbatim intinya): void where prohibited; 18+;
**Ends December 5, 2026, 11:59pm EST**; pemenang dipilih atas diskresi Base/partner dan
diberitahu via email; pemenang kena identity verification + kewajiban pajak;
**"Any projects that enable trading for U.S. users are not in scope"**.

---

## Jawaban siap tempel

**Project name**
StockMaxx Agent

**Track**
Agentic Stock Finance  ← (satu-satunya track yang dimasuki; aturan: maks 1 submission per Track)

**Link to X post**
[ISI SETELAH POSTING — URL post @KenzieRefa berisi video demo + tag @buildonbase]

**Project / repo link**
https://github.com/Abdul99090/stockmaxx-agent

**Demo video link (bila diminta terpisah dari post X)**
File lokal: video/demo.mp4 (dilampirkan di post X; bila form minta URL, upload file yang sama dan tempel URL-nya)

**Short description (1–2 kalimat)**
StockMaxx Agent is an AI agent that watches tokenized stocks on Base, scores them with a momentum/consistency signal engine protected by a NAV-staleness guard, and manages a paper portfolio on Base Sepolia under hard risk caps (20% per position, 60% max exposure, stop-loss/take-profit, kill switch).

**Long description / what it does**
The agent reads tokenized-stock reference data the way Base documents it — the public Tokenized Stocks API (token contracts, total supply, multiplier, Chainlink-based NAV) — and tracks positions in share-equivalent units using the multiplier (balanceOfUI concept). Every candidate order is scored by the signal engine, then must pass the risk guard; blocked orders are logged with the reason. Each executed intent is written to an append-only ledger anchored to the live Base Sepolia block height at decision time. A mainnet router adapter (Aerodrome) exists only as a disabled stub: no real funds are used in this submission, and enabling mainnet execution is a separate, explicit human decision.

**What was built during the Quest Period (5 Nov – 5 Des 2026)**
Everything in this repo: the agent (data layer, signal engine, risk guard, paper executor, reporting), its test suite, the recorded demo run, and the demo video. The signal/risk patterns are adapted from the builder's own pre-existing on-chain monitoring tooling; all Stocks Maxxing code was written during the Quest Period. (Aturan Bagian 6 memang mewajibkan form menjelaskan apa yang dibangun selama periode Quest.)

**Network**
Base Sepolia (testnet), chain id 84532. Per Official Rules Section 5: "No purchase, transaction, wallet funding, token holding, or payment of any kind is required to enter... Entrants may use a Base testnet. Testnet Submissions will not be judged less favorably."

**Does the project enable trading for U.S. users?**
No. StockMaxx Agent is a single-operator portfolio agent that runs for its owner's own wallet in paper/testnet mode. It is not offered as a trading service to the public or to U.S. users, and it places no real orders in this submission.

**Token launch**
None. The project launches no token (the Quest states launching a token is optional).

**Team**
Solo builder. [Nama/handle sesuai identitas akun yang dipakai submit — agen utama isi:
handle X @KenzieRefa adalah akun yang memposting demo; identitas entrant harus konsisten
dari post sampai form (aturan Bagian 5: "Each Entrant must use the same identity
throughout the Quest"; submission lewat banyak akun/identitas lain = void).]

**Contact email**
[ISI — email yang aktif dipantau; pemenang diberitahu via email/X DM dan wajib merespons
dalam 7 hari + identity verification + form pajak W-9/W-8/bentuk lokal (aturan Bagian 9).]

**Wallet address for prize (bila diminta)**
[ISI — alamat Base yang benar & bisa diakses; hadiah dibayar USDC on Base (aturan Bagian 10).
JANGAN pakai alamat yang tidak dikuasai penuh.]

**Anything else / notes for judges**
Demo is fully reproducible from the repo with zero dependencies (Python stdlib), zero API keys, and zero wallet keys: `python3 src/stockmaxx_agent.py --ticks 10`. The recorded run (output/demo_transcript.txt) bought 3 positions, had later orders vetoed by the exposure cap, and finished +1.01% on paper — the guard vetoing the signal engine is the point of the design.

---

## Checklist sebelum submit (agen utama)
1. [ ] Post X live dari @KenzieRefa: video demo.mp4 terlampir + tag @buildonbase + teks = draft-post.txt post utama.
2. [ ] Repo GitHub publik ter-push (akun Abdul99090) dan URL-nya dimasukkan ke jawaban di atas + ke thread post bila jadi thread.
3. [ ] Submit form SEBELUM deadline aman: **target ≤ 5 Des 2026 siang WIB** (lihat catatan deadline di laporan — rules vs form beda zona; jangan mepet).
4. [ ] Identitas entrant konsisten: akun X yang posting = identitas di form.
5. [ ] Sesudah submit: simpan screenshot/bukti submit + tanggalnya di folder ini.
