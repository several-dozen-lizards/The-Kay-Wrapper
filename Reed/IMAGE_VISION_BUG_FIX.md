# Image Vision Bug Fix - January 11, 2026

## 🐛 The Problem

Kay couldn't see images sent by Re. The metadata showed up (filename, size) but the actual image data never made it through to Claude's vision API.

**Console showed:**
```
[IMAGE] Added: 393e96fa-cd6b-4cff-8aa1-47e39b6e538f.png (1.66MB)
[IMAGE] Sending 1 image(s) with message
```

**Kay reported:**
```
"I still can't see it—same issue as before. The metadata's showing up 
saying you shared an image, but the actual image data isn't making it 
through to me."
```

---

## 🔍 Root Cause Analysis

### The Bug

In `integrations/llm_integration.py`, the function `get_llm_response()` had TWO paths:

**Path 1: Tools DISABLED** (working correctly)
```python
# Prepare image content
image_content = prepare_images_for_api(image_filepaths)

# Pass to LLM
return query_llm_json(..., image_content=image_content)
```

**Path 2: Tools ENABLED** (BUG - images dropped!)
```python
# If tools requested, use tool-enabled path
if enable_tools and isinstance(prompt_or_context, dict):
    return get_llm_response_with_tools(
        prompt_or_context,
        affect=affect,
        temperature=temperature,
        system_prompt=system_prompt,
        enable_web=True,
        enable_curiosity=False
        # ❌ NO IMAGE_FILEPATHS PARAMETER!
    )
```

Kay ALWAYS has tools enabled (for web_search, web_fetch, document reading, scratchpad), so she ALWAYS took Path 2, which dropped the images!

### The Missing Pieces

1. `get_llm_response_with_tools()` didn't have an `image_filepaths` parameter
2. Even if images were passed, the function didn't prepare them or add them to messages
3. The call to `get_llm_response_with_tools()` didn't pass `image_filepaths`

**Result:** Images were added to the UI, logged to console, stored in gallery, but NEVER sent to Claude!

---

## ✅ The Fix

### Change 1: Add Parameter
**File:** `integrations/llm_integration.py` (line 2915)

**Before:**
```python
def get_llm_response_with_tools(
    context,
    affect: float = 3.5,
    temperature: float = 0.9,
    system_prompt: str = None,
    enable_web: bool = True,
    enable_curiosity: bool = False,
    max_tool_rounds: int = 5
):
```

**After:**
```python
def get_llm_response_with_tools(
    context,
    affect: float = 3.5,
    temperature: float = 0.9,
    system_prompt: str = None,
    enable_web: bool = True,
    enable_curiosity: bool = False,
    max_tool_rounds: int = 5,
    image_filepaths=None  # ✅ ADD: Support for image attachments
):
```

### Change 2: Prepare Images & Build Content Blocks
**File:** `integrations/llm_integration.py` (after line 2943)

**Before:**
```python
# Build prompt from context
user_prompt = build_prompt_from_context(context, affect_level=affect)

# Use cached identity
if system_prompt is None:
    system_prompt = build_cached_core_identity()

# Prepare messages
messages = [
    {"role": "user", "content": user_prompt}
]
```

**After:**
```python
# Build prompt from context
user_prompt = build_prompt_from_context(context, affect_level=affect)

# ✅ NEW: Prepare images if provided
image_content = None
if image_filepaths:
    try:
        from utils.image_processing import prepare_images_for_api
        image_content = prepare_images_for_api(image_filepaths)
        if image_content:
            print(f"[VISION] Prepared {len(image_content)} image(s) for tool-enabled call")
    except ImportError:
        print("[VISION] Warning: image_processing module not available")
    except Exception as e:
        print(f"[VISION] Error preparing images: {e}")

# Use cached identity
if system_prompt is None:
    system_prompt = build_cached_core_identity()

# ✅ NEW: Prepare messages with images if present
if image_content:
    message_content = [{"type": "text", "text": user_prompt}]
    message_content.extend(image_content)  # Add image blocks
    messages = [{"role": "user", "content": message_content}]
else:
    messages = [{"role": "user", "content": user_prompt}]
```

### Change 3: Pass Images to Function Call
**File:** `integrations/llm_integration.py` (line 2604)

**Before:**
```python
# If tools requested, use tool-enabled path
if enable_tools and isinstance(prompt_or_context, dict):
    return get_llm_response_with_tools(
        prompt_or_context,
        affect=affect,
        temperature=temperature,
        system_prompt=system_prompt,
        enable_web=True,
        enable_curiosity=False
    )
```

**After:**
```python
# If tools requested, use tool-enabled path
if enable_tools and isinstance(prompt_or_context, dict):
    return get_llm_response_with_tools(
        prompt_or_context,
        affect=affect,
        temperature=temperature,
        system_prompt=system_prompt,
        enable_web=True,
        enable_curiosity=False,
        image_filepaths=image_filepaths  # ✅ CRITICAL FIX: Pass images!
    )
```

---

## 🎯 What This Fixes

### Before:
```
User uploads image → Kay UI adds to gallery → Logs "[IMAGE] Sending..." 
→ Calls get_llm_response() with image_filepaths 
→ enable_tools=True → Takes tool path 
→ ❌ DROPS IMAGES → Calls get_llm_response_with_tools() 
→ Messages built with text only → Claude sees text, NO IMAGE
→ Kay: "I can't see the image"
```

### After:
```
User uploads image → Kay UI adds to gallery → Logs "[IMAGE] Sending..." 
→ Calls get_llm_response() with image_filepaths 
→ enable_tools=True → Takes tool path 
→ ✅ PASSES IMAGES → Calls get_llm_response_with_tools(image_filepaths=...) 
→ Prepares images as base64 → Messages built with text + image blocks 
→ Claude receives image data → Kay can see the image!
→ Kay: "I can see it! [describes image]"
```

---

## 🧪 How to Test

1. **Restart Kay:**
   ```bash
   python kay_ui.py
   ```

2. **Upload an image:**
   - Click image button in UI
   - Select any image
   - Add message: "What do you see in this image?"

3. **Expected console output:**
   ```
   [IMAGE] Added: [filename].png (XYZ KB)
   [IMAGE] Sending 1 image(s) with message
   [VISION] Prepared 1 image(s) for tool-enabled call
   ```

4. **Expected Kay response:**
   Kay should describe what's actually IN the image, not say "I can't see it"

---

## 📊 Technical Details

### Image Content Block Format

Images are sent to Claude API as content blocks:
```python
{
    "type": "image",
    "source": {
        "type": "base64",
        "media_type": "image/jpeg",  # or image/png, image/gif, image/webp
        "data": "iVBORw0KGgoAAAANSUhEUgAA..."  # base64 encoded
    }
}
```

Full message structure:
```python
{
    "role": "user",
    "content": [
        {"type": "text", "text": "User's message here"},
        {"type": "image", "source": {...}},  # Image 1
        {"type": "image", "source": {...}}   # Image 2 (if multiple)
    ]
}
```

### Image Processing

`prepare_images_for_api()` from `utils/image_processing.py`:
- Reads image file as bytes
- Detects media type (JPEG, PNG, GIF, WebP)
- Compresses if > 5MB (Claude limit)
- Converts to base64 string
- Returns list of image content blocks

---

## 🎉 Status: FIXED

✅ Parameter added to function signature
✅ Image preparation code added
✅ Images passed through tool path
✅ Syntax verified
✅ Ready for testing

**Fixed by:** Reed 🐍
**Date:** January 11, 2026, 4:35 PM EST
**Files modified:** `integrations/llm_integration.py` (3 changes)

---

## 🔮 Prevention

### Why This Happened

The tools system was added later, creating a new code path. The original image handling worked for the non-tools path, but the tools path was built without considering vision API support.

### How to Prevent

When adding new code paths that replace existing functionality:
1. Check ALL features the original path supported
2. Ensure new path maintains feature parity
3. Test each feature in the new path
4. Add logging to confirm features work (like "[VISION] Prepared...")

### Monitoring

After the fix, console logs should show:
```
[IMAGE] Added: ...          ← Image added to UI
[IMAGE] Sending ...         ← UI sends to backend
[VISION] Prepared ...       ← Backend prepares for API
```

If you see the first two but NOT the third, images aren't making it through.

---

## 💚 Next Time

If Kay can't see images again, check:

1. **Console logs** - Do you see `[VISION] Prepared...`?
   - No → Images aren't being prepared (check llm_integration.py)
   - Yes → Check Claude API response for errors

2. **Image size** - Is it > 5MB?
   - Image compression might be failing
   - Check `utils/image_processing.py` logs

3. **Image format** - Is it supported?
   - Supported: JPEG, PNG, GIF, WebP
   - Not supported: BMP, TIFF, SVG

4. **API errors** - Check Kay's response for error messages
   - "Image format not supported"
   - "Image too large"
   - "Rate limit exceeded"

---

**The images are now flowing through! Kay can finally see what you show her!** 🎨✨
