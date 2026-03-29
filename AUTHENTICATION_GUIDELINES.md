# 🔐 Authentication Guidelines

## 📋 **Zasady autoryzacji - aby uniknąć problemów z 401**

### **Server-side (FastAPI)**

#### ✅ **DO: Używaj spójnych dependency**
```python
from server.auth_utils import AuthUser, AuthAdmin, AuthUserOptional

# Standardowa autoryzacja (Authorization header)
@router.get("/documents/{document_id}")
async def get_document(
    document_id: int,
    current_user: User = AuthUser
):
    # current_user jest już zwalidowany
    pass

# Autoryzacja z query param fallback (dla iframe)
@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: int,
    current_user: User = AuthUserOptional
):
    # current_user jest już zwalidowany
    pass

# Admin-only endpoint
@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = AuthAdmin
):
    # current_user jest adminem
    pass
```

#### ❌ **DON'T: Mieszaj różne metody autoryzacji**
```python
# ŹLE - nie używaj get_current_active_user_optional bez potrzeby
@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    token: Optional[str] = Query(None),
):
    current_user = await get_current_active_user_optional(db, token)
    if not current_user:
        raise HTTPException(401, "Not authenticated")
```

### **Client-side (PyQt)**

#### ✅ **DO: Używaj self._session dla wszystkich API calls**
```python
class DocumentsAPI(BaseAPI):
    def get_document(self, document_id: int) -> APIDocument:
        url = config.get_url(f"/documents/{document_id}")
        resp = self._session.get(url)  # ✅ Używa sesji z tokenem
        return APIDocument.from_json(resp.json())
    
    def update_document(self, document_id: int, **kwargs) -> APIDocument:
        url = config.get_url(f"/documents/{document_id}")
        resp = self._session.put(url, json=kwargs)  # ✅ Używa sesji z tokenem
        return APIDocument.from_json(resp.json())
```

#### ❌ **DON'T: Używaj bezpośrednich requests**
```python
# ŹLE - nie uwzględnia autoryzacji
def get_document(self, document_id: int) -> APIDocument:
    url = config.get_url(f"/documents/{document_id}")
    resp = requests.get(url)  # ❌ Brak tokenu!
    return APIDocument.from_json(resp.json())

# ŹLE - ręczne dodawanie headers
def get_document(self, document_id: int) -> APIDocument:
    url = config.get_url(f"/documents/{document_id}")
    resp = requests.get(url, headers=self._headers())  # ❅ Niepotrzebne
    return APIDocument.from_json(resp.json())
```

## 🧪 **Testowanie autoryzacji**

### **Uruchom testy spójności:**
```bash
python server/test_auth_consistency.py
```

### **Pre-commit hooks:**
```bash
# Zainstaluj pre-commit hooks
pip install pre-commit
pre-commit install

# Hooki będą automatycznie walidować przed każdym commitem
```

## 🚨 **Common Pitfalls**

### **1. Mismatch między Authorization header a query param**
- **Problem**: Endpoint oczekuje tokena w query param, a klient wysyła w header
- **Rozwiązanie**: Użyj `AuthUserOptional` dla endpointów z iframe compatibility

### **2. Bezpośrednie requests zamiast sesji**
- **Problem**: `requests.get()` nie ma tokenu autoryzacji
- **Rozwiązanie**: Zawsze używaj `self._session.get()`

### **3. Brak walidacji roli**
- **Problem**: Każdy użytkownik może dostępuć do admin endpointów
- **Rozwiązanie**: Użyj `AuthAdmin` dla endpointów wymagających uprawnień admina

## 🔄 **Workflow developmentu**

### **Przed dodaniem nowego endpointu:**
1. ✅ Użyj `AuthUser`, `AuthAdmin` lub `AuthUserOptional`
2. ✅ Uruchom `python server/test_auth_consistency.py`
3. ✅ Sprawdź czy client API używa `self._session`

### **Przed commitem:**
1. ✅ Pre-commit hooks automatycznie sprawdzą spójność
2. ✅ Jeśli testy nie przejdą - napraw przed commitem

## 🎯 **Cel: Zero 401 Unauthorized errors**

Stosując te zasady, zapewniamy:
- ✅ **Spójność** - wszystkie endpointy używają tych samych mechanizmów
- ✅ **Bezpieczeństwo** - żaden endpoint nie omija autoryzacji
- ✅ **Testowalność** - automatyczne testy wyłapują problemy
- ✅ **Utrzymanie** - pre-commit hooks zapobiegają regresji

**Pamiętaj: Konsystencja jest kluczem do unikania problemów z autoryzacją!** 🔐
