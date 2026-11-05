**Scoped verdict: READY** for the seven HTTP formats and the available SDK-client checks.

Using the installed OpenAI, Anthropic, and Hugging Face clients against the existing service:

- OpenAI normal and streaming calls both reconstructed raw **T1** and policy **T3**; streaming finished with `stop`.
- Anthropic normal and streaming calls likewise returned raw **T1** and policy **T3**; streaming ended with `end_turn`.
- Hugging Face `text_classification` returned the expected three scores, with T1 highest.
- The scope headers were accepted by both chat clients; Hugging Face received them via client headers.
- Triton remains **unverified** because `tritonclient` is unavailable. Pytest was not run.

A probe cleanup call raised `AttributeError` because this installed `InferenceClient` has no `.close()` method; the classification call had already succeeded. No files or processes were changed.

The ten SHA-256 hashes match the prior checkpoint:

```text
shunt/protocols.py       480BAD6EAEE7198CD1977975604505AE6F84AB08482AE1D8060DC2B7E2AF297F
shunt/decision.py        FCB6104F4D1478FEEF0C4D21F507137C69A73D9DA155E872C369654A8B21F1CB
shunt/systemone.py       CE9FBD4237DA34183A22AEE2B9FC4D073B97DA8D388B41A92E193CFB908C2231
shunt/server.py          9C26DFF495FC84FB4DCBDE3429D40F07FB7D96EB235EAF94BD2D02C04FE2E6AD
tests/test_protocols.py  CA20C2FAE3B6E9D5484971315C44F9D8DFF762800BCE306CFFACD47512E5A7AF
tests/test_config.py     89D9644EFC98ADED141255E48DA5FFC00640EC50006786B8ED4EA2C00A11BDC1
docs/api.md              ED6F25F00427C2E29AE2D03A5DF81EFE28F9FB77D871325310FF4335C84B9E86
README.md                E33B6AE23421B77DEB5BFA345585BF7DE63F3714F5F629EC8B0B6D85F02CCC6D
requirements-dev.txt     A142B19E9DC1F628069FF506B3FD0BFCF1413848EF059AB5CD0C6FF2C95DB916
scripts/check_api.py     280280CC14597BB0F81F5D6A4A0007ED3997D754D117E000F92D93BA549B462
```