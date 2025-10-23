package com.example.anime_recommender_app

import android.content.Context
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

class PythonHelper(private val context: Context) {
    
    fun initPython() {
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(context))
        }
    }
    
    fun testPython(): String {
        return try {
            val python = Python.getInstance()
            val module = python.getModule("main")
            module.callAttr("test_function").toString()
        } catch (e: Exception) {
            "Error: ${e.message}"
        }
    }
    
    fun getRecommendations(preferencesJson: String): String {
        return try {
            val python = Python.getInstance()
            val module = python.getModule("main")
            val result = module.callAttr("get_mobile_recommendations", preferencesJson)
            result.toString()
        } catch (e: Exception) {
            "{\"error\": \"${e.message}\"}"
        }
    }
    
    fun getUserStatistics(): String {
        return try {
            val python = Python.getInstance()
            val module = python.getModule("main")
            val result = module.callAttr("get_user_statistics")
            result.toString()
        } catch (e: Exception) {
            "{\"error\": \"${e.message}\"}"
        }
    }
    
    fun initRecommender(): String {
        return try {
            val python = Python.getInstance()
            val module = python.getModule("main")
            module.callAttr("init_mobile_recommender").toString()
        } catch (e: Exception) {
            "Error: ${e.message}"
        }
    }
}