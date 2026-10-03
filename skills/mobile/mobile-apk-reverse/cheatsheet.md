# APK reversing cheatsheet — Frida hook recipes

Companion to `SKILL.md`. Run with `frida -U -f com.example.app -l hook.js`. Adapt class names to
the target. Print before you override: observe arguments/returns first, then change behavior.

## Generic method hook

```javascript
Java.perform(function() {
    var C = Java.use("com.target.ClassName");
    C.methodName.overload('java.lang.String', 'int').implementation = function(str, num) {
        console.log("[*] methodName(" + str + ", " + num + ")");
        var ret = this.methodName(str, num);
        console.log("[*] return: " + ret);
        return ret;
    };
});
```

Hook a constructor via `C.$init.overload(...)`; enumerate a class's methods with
`C.class.getDeclaredMethods().forEach(m => console.log(m.toString()))`.

## Crypto capture (keys, IVs, plaintext)

```javascript
Java.perform(function() {
    var Cipher = Java.use("javax.crypto.Cipher");
    Cipher.doFinal.overload('[B').implementation = function(input) {
        console.log("[Cipher.doFinal] input=" + bytesToHex(input));
        var out = this.doFinal(input);
        console.log("[Cipher.doFinal] output=" + bytesToHex(out));
        return out;
    };
    Java.use("javax.crypto.spec.SecretKeySpec").$init.overload('[B', 'java.lang.String')
        .implementation = function(key, algo) {
            console.log("[SecretKeySpec] algo=" + algo + " key=" + bytesToHex(key));
            this.$init(key, algo);
        };
    Java.use("javax.crypto.spec.IvParameterSpec").$init.overload('[B')
        .implementation = function(iv) {
            console.log("[IV] " + bytesToHex(iv));
            this.$init(iv);
        };
});
```

Same pattern for `java.security.MessageDigest.digest` (hash inputs/outputs) and
`javax.crypto.Mac.doFinal` / `Mac.init` (HMAC inputs and keys — `key.getEncoded()`).

## Network observation

```javascript
// OkHttp3: method, URL, headers, response code
Java.perform(function() {
    var RealCall = Java.use("okhttp3.RealCall");
    RealCall.execute.implementation = function() {
        var req = this.request();
        console.log("[OkHttp] " + req.method() + " " + req.url().toString());
        var h = req.headers();
        for (var i = 0; i < h.size(); i++) console.log("  " + h.name(i) + ": " + h.value(i));
        var resp = this.execute();
        console.log("[OkHttp] -> " + resp.code());
        return resp;
    };
});
```

Also useful: `java.net.URL.openConnection` (log `this.toString()`), `android.webkit.WebView.loadUrl`
and `evaluateJavascript` (log URLs/scripts crossing the JS bridge).

## SSL pinning bypass (generic)

```javascript
Java.perform(function() {
    try {  // OkHttp3 CertificatePinner
        Java.use("okhttp3.CertificatePinner").check
            .overload('java.lang.String', 'java.util.List').implementation = function() {
                console.log("[*] pinning bypassed (OkHttp3)");
            };
    } catch (e) {}
    try {  // Conscrypt TrustManagerImpl
        Java.use("com.android.org.conscrypt.TrustManagerImpl").verifyChain
            .implementation = function(chain) {
                console.log("[*] pinning bypassed (TrustManagerImpl)");
                return chain;
            };
    } catch (e) {}
});
```

Wrap every target in try/catch so one missing class doesn't kill the script. For the full
technique (network-security-config, custom TrustManagers, native pinning): `mobile-cert-pinning-bypass`.
Ready-made kits: httptoolkit/frida-interception-and-unpinning, Frida CodeShare.

## Root / emulator / anti-debug bypass

```javascript
Java.perform(function() {
    // Hide root artifacts from File.exists
    var rootPaths = ["su", "magisk", "busybox", "Superuser", "/system/xbin/su", "/sbin/su"];
    var File = Java.use("java.io.File");
    File.exists.implementation = function() {
        var p = this.getAbsolutePath();
        for (var i = 0; i < rootPaths.length; i++)
            if (p.toLowerCase().indexOf(rootPaths[i].toLowerCase()) !== -1) return false;
        return this.exists();
    };
    // Block "su" / "which" probes
    Java.use("java.lang.Runtime").exec.overload('java.lang.String').implementation = function(cmd) {
        if (cmd.indexOf("su") !== -1 || cmd.indexOf("which") !== -1)
            throw Java.use("java.io.IOException").$new("Permission denied");
        return this.exec(cmd);
    };
    // Release-keys + debugger check
    Java.use("android.os.Build").TAGS.value = "release-keys";
    Java.use("android.os.Debug").isDebuggerConnected.implementation = function() { return false; };
});
```

Emulator spoof: overwrite `Build.FINGERPRINT/MODEL/MANUFACTURER/BRAND/DEVICE/HARDWARE` with real
device values and stub `TelephonyManager.getDeviceId/getSubscriberId/getSimSerialNumber` to
plausible constants.

## Storage observation

```javascript
// SharedPreferences read/write
Java.perform(function() {
    Java.use("android.app.SharedPreferencesImpl").getString.implementation = function(k, d) {
        var v = this.getString(k, d);
        console.log("[SP.get] " + k + " = " + v);
        return v;
    };
});
// SQLite
Java.use("android.database.sqlite.SQLiteDatabase").rawQuery.implementation = function(sql, args) {
    console.log("[SQL] " + sql);
    return this.rawQuery(sql, args);
};
```

## Unpacking helpers

Enumerate loaded DEX via `Java.enumerateClassLoaders` (cast each to
`dalvik.system.BaseDexClassLoader` and walk `pathList.dexElements` — packed apps decrypt DEX at
runtime; enumerate first, then dump). Hook `ClassLoader.loadClass` filtered on the app package to
watch classes materialize.

## Utility functions

```javascript
function bytesToHex(b) {
    if (!b) return "null";
    var h = [];
    for (var i = 0; i < b.length; i++) h.push(('0' + (b[i] & 0xFF).toString(16)).slice(-2));
    return h.join('');
}
function printStack() {  // where am I called from
    console.log(Java.use("android.util.Log").getStackTraceString(
        Java.use("java.lang.Throwable").$new()));
}
Java.choose("com.target.ClassName", {   // find live instances, dump fields
    onMatch: function(inst) { console.log("[instance] " + inst); },
    onComplete: function() {}
});
```

## frida-server setup

```bash
pip install frida-tools
adb push frida-server /data/local/tmp/
adb shell chmod 755 /data/local/tmp/frida-server
adb shell su -c /data/local/tmp/frida-server &
frida -U -f com.example.app -l hook.js
```

Match the frida-server version/arch to both the device and your client frida-tools version —
mismatches are the most common cause of silent attach failures.

---
_Portions adapted from [reverse-skill](https://github.com/zhaoxuya520/reverse-skill) by zhaoxuya520, MIT License._
