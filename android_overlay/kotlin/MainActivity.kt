package com.codewars.game

import com.chaquo.python.PyObject
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import org.json.JSONObject
import kotlin.concurrent.thread

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        if (!Python.isStarted()) Python.start(AndroidPlatform(this))
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "codewars/python")
            .setMethodCallHandler { call, result ->
                if (call.method != "run") { result.notImplemented(); return@setMethodCallHandler }
                val src = call.argument<String>("source") ?: ""
                thread {
                    try {
                        val mod = Python.getInstance().getModule("runner")
                        val r: PyObject = mod.callAttr("run_script", src)
                        val map = HashMap<String, Any?>()
                        for ((k, v) in r.asMap()) map[k.toString()] = v.toJava(Any::class.java)
                        runOnUiThread { result.success(JSONObject(map).toString()) }
                    } catch (e: Exception) {
                        runOnUiThread { result.error("PY", e.message, null) }
                    }
                }
            }
    }
}
