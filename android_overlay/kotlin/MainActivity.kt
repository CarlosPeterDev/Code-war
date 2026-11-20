package com.codewars.game

import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.util.concurrent.Executors

/**
 * Bridges Flutter to the embedded CPython runtime (Chaquopy).
 * The MethodChannel method name is the name of a function in the Python module `codewars.bridge`;
 * arguments are passed positionally and every function returns a JSON string.
 * All calls run on ONE worker thread so game state is mutated strictly in call order.
 */
class MainActivity : FlutterActivity() {
    private val worker = Executors.newSingleThreadExecutor()

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        if (!Python.isStarted()) Python.start(AndroidPlatform(this))
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "codewars/py")
            .setMethodCallHandler { call, result ->
                val args: List<Any?> = (call.arguments as? List<*>) ?: emptyList<Any?>()
                worker.execute {
                    try {
                        val mod = Python.getInstance().getModule("codewars.bridge")
                        val out = mod.callAttr(call.method, *args.toTypedArray())
                        val text = out?.toString()
                        runOnUiThread { result.success(text) }
                    } catch (e: Throwable) {
                        runOnUiThread { result.error("PY", e.message ?: e.toString(), null) }
                    }
                }
            }
    }

    override fun onDestroy() {
        worker.shutdown()
        super.onDestroy()
    }
}
