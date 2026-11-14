package com.spotifree.app;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.os.Bundle;
import com.getcapacitor.BridgeActivity;
import com.getcapacitor.CapConfig;

/**
 * Online → Capacitor config loads live Render UI ({@code server.url}).
 * Offline → clear {@code server.url} so the WebView serves bundled {@code dist/} immediately
 * (avoids waiting on {@code errorPath} timeout when the device has no network).
 */
public class MainActivity extends BridgeActivity {

    @Override
    public void onCreate(Bundle savedInstanceState) {
        if (!isNetworkAvailable()) {
            // No serverUrl → local assets under webDir. Keep https://localhost scheme.
            this.config =
                new CapConfig.Builder(this)
                    .setAndroidScheme("https")
                    .setHostname("localhost")
                    .setAllowMixedContent(true)
                    .setErrorPath("index.html")
                    .create();
        }
        super.onCreate(savedInstanceState);
    }

    private boolean isNetworkAvailable() {
        ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
        if (cm == null) {
            return false;
        }
        Network network = cm.getActiveNetwork();
        if (network == null) {
            return false;
        }
        NetworkCapabilities caps = cm.getNetworkCapabilities(network);
        if (caps == null) {
            return false;
        }
        // Prefer INTERNET without VALIDATED so brief captive-portal / DNS lag still
        // tries the live Render UI (errorPath covers true reachability failures).
        return caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET);
    }
}
