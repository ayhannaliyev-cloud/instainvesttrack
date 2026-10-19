# ABB Invest Instagram

ABB Invest və rəqiblərinin (PAŞA Kapital, InvestAZ, Unicapital, CFI, Birbank Invest, Troni) açıq Instagram rəqəmlərini göstərən səhifə.
Rəqəmlər Instagram-a daxil olmadan, açıq profil səhifələrindən yığılır.

- `accounts.json`: izlənən hesablar. Hesab əlavə etmək və ya silmək üçün bu faylı dəyişin.
- `scripts/scrape.py`: profilləri brauzerdə açıb rəqəmləri yığır və `docs/data/` qovluğuna yazır.
- `docs/index.html`: komandanın baxdığı səhifə.
- `.github/workflows/update.yml`: GitHub-da yeniləməni işə salan tapşırıq.

## Qurulma (bir dəfə)

1. GitHub-da yeni **public** repository yaradın, məsələn `abb-instagram`.
2. Bu qovluqdakı faylların hamısını həmin repository-yə yükləyin (`.github` qovluğu da daxil olmaqla).
3. Repository-də **Settings → Pages** bölməsinə keçin:
   - **Source**: `Deploy from a branch`
   - **Branch**: `main`, qovluq `/docs` → **Save**
4. Bir neçə dəqiqədən sonra səhifə `https://<istifadəçi-adınız>.github.io/abb-instagram/` ünvanında açılır. Bu linki komandaya göndərin.

## Rəqəmləri yeniləmək

- **Actions** → **Instagram rəqəmlərini yenilə** → **Run workflow**.
- Bir-iki dəqiqəyə yeni rəqəmlər saxlanılır, səhifə də bir neçə dəqiqəyə yenilənir.
- Səhifənin yuxarısında "Son yeniləmə" tarixi göstərilir.

## Gündəlik yoxlamanı yandırmaq və söndürmək

`.github/workflows/update.yml` faylında `schedule:` və `cron:` sətirlərinin əvvəlindəki `#` işarəsini silin.
Bundan sonra yoxlama hər gün saat 09:00-da (Bakı vaxtı) özü işləyəcək. Söndürmək üçün `#` işarəsini geri qoyun.
Alternativ yol: **Actions** → tapşırıq → **⋯** → **Disable workflow**.

## GitHub-dan bloklansa

Instagram GitHub serverlərindən gələn sorğuları bloklaya bilər. Bu halda Actions-da hesablar `FAIL` kimi görünür,
səhifə isə son uğurlu rəqəmləri göstərməyə davam edir. Onda yeniləməni öz Mac-inizdən edə bilərsiniz:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
.venv/bin/python scripts/scrape.py
```

Sonra dəyişən `docs/data/` fayllarını GitHub-a yükləyin (commit + push).
