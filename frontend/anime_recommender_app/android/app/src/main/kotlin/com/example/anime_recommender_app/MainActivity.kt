package com.example.anime_recommender_app

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import org.json.JSONObject

class MainActivity: FlutterActivity() {
    private val CHANNEL = "com.example.anime_recommender_app/python"
    private lateinit var pythonHelper: PythonHelper

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        
        pythonHelper = PythonHelper(this)
        pythonHelper.initPython()

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->

            when (call.method) {
                "testPython" -> {
                    val testResult = pythonHelper.testPython()
                    result.success(testResult)
                }
                "getRecommendations" -> {
                    try {
                        val preferences = call.arguments as? Map<*, *>
                        val preferencesJson = JSONObject(preferences ?: emptyMap<Any?, Any?>()).toString()
                        val recommendations = pythonHelper.getRecommendations(preferencesJson)
                        result.success(recommendations)
                    } catch (e: Exception) {
                        result.error("ERROR", "Failed to process preferences: ${e.message}", null)
                    }
                }
                "getUserStatistics" -> {
                    try {
                        val stats = pythonHelper.getUserStatistics()
                        result.success(stats)
                    } catch (e: Exception) {
                        result.error("ERROR", "Failed to get user statistics: ${e.message}", null)
                    }
                }
                "initRecommender" -> {
                    try {
                        val initResult = pythonHelper.initRecommender()
                        result.success(initResult)
                    } catch (e: Exception) {
                        result.error("ERROR", "Failed to initialize recommender: ${e.message}", null)
                    }
                }
                else -> result.notImplemented()
            }
        }
    }
}