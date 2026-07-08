/**
 * ════════════════════════════════════════════════════════════════
 *  STOCKBOY PREMIUM — REAL-TIME FIREBASE NOTIFICATIONS ENGINE
 *  Listens to Firestore and dispatches events to Toast and Center
 * ════════════════════════════════════════════════════════════════
 */

import { getFirestore, collection, query, where, orderBy, limit, onSnapshot } 
  from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js';

window.StockboyNotifications = (function() {
  'use strict';

  let db = null;
  let uid = null;
  
  let isInitialSignalLoad = true;
  let isInitialNotifLoad = true;

  // We need to wait for Firebase Auth to initialize, which happens in base.html or auth.html
  function initListeners() {
    if (!window.firebaseAuth) {
      setTimeout(initListeners, 500);
      return;
    }

    window.firebaseAuth.onAuthStateChanged((user) => {
      if (user) {
        uid = user.uid;
        if (!db) {
          db = getFirestore();
          startSignalListener();
          startNotificationListener();
        }
      }
    });
  }

  function startSignalListener() {
    const q = query(
      collection(db, "stockSignals"), 
      orderBy("createdAt", "desc"), 
      limit(20)
    );

    onSnapshot(q, (snapshot) => {
      snapshot.docChanges().forEach((change) => {
        const data = change.doc.data();
        const docId = change.doc.id;

        if (change.type === 'added') {
          if (!isInitialSignalLoad) {
            // New signal published!
            const isBuy = data.recommendation === 'BUY';
            window.StockboyToast.show({
              title: `${isBuy ? '🟢 BUY' : '🔴 SELL'} Signal`,
              message: `${data.stockName}\nCMP: ₹${data.entryPrice}\nTarget: ₹${data.target1}`,
              type: isBuy ? 'signal-buy' : 'signal-sell',
              duration: 8000
            });
            
            window.StockboyNotificationCenter.add({
              id: docId,
              title: `New ${data.recommendation} Signal: ${data.stockName}`,
              message: `Entry: ₹${data.entryPrice} | T1: ₹${data.target1}`,
              timestamp: data.createdAt ? new Date(data.createdAt).getTime() : Date.now(),
              read: false
            });
          }
        }
        
        if (change.type === 'modified') {
          if (!isInitialSignalLoad) {
            if (data.status === 'TARGET HIT' || data.status === 'Target Hit') {
              window.StockboyToast.show({
                title: `Target Hit 🎯`,
                message: `${data.stockName} has reached its target!`,
                type: 'success'
              });
            } else if (data.status === 'STOP LOSS HIT' || data.status === 'Stop Loss Hit') {
              window.StockboyToast.show({
                title: `Stop Loss Triggered`,
                message: `${data.stockName} hit the stop loss.`,
                type: 'error'
              });
            } else if (data.status === 'CLOSED' || data.status === 'Closed') {
              window.StockboyToast.show({
                title: `Signal Closed`,
                message: `${data.stockName} trade has been closed.`,
                type: 'info'
              });
            }
          }
        }
      });
      isInitialSignalLoad = false;
    });
  }

  function startNotificationListener() {
    // Listen to global announcements and user-specific notifications
    const q = query(
      collection(db, "notifications"), 
      where("userId", "in", ["global", uid]),
      orderBy("createdAt", "desc"), 
      limit(50)
    );

    onSnapshot(q, (snapshot) => {
      const history = [];
      
      snapshot.forEach((doc) => {
        const data = doc.data();
        history.push({
          id: doc.id,
          title: data.title,
          message: data.message,
          type: data.type || 'info', // success, warning, error, info
          timestamp: data.createdAt ? new Date(data.createdAt).getTime() : Date.now(),
          read: data.readStatus ? data.readStatus.includes(uid) : false
        });
      });

      // Sync history with Notification Center
      window.StockboyNotificationCenter.sync(history);

      // Handle new incoming toasts
      snapshot.docChanges().forEach((change) => {
        if (change.type === 'added' && !isInitialNotifLoad) {
          const data = change.doc.data();
          window.StockboyToast.show({
            title: data.title,
            message: data.message,
            type: data.type || 'info',
            duration: 8000
          });
        }
      });
      
      isInitialNotifLoad = false;
    });
  }

  // Admin function to publish global announcements
  async function publishAnnouncement(title, message, type = 'info') {
    if (!db) {
      alert("Database not initialized");
      return false;
    }
    try {
      // Lazy import addDoc to save memory if not admin
      const { addDoc } = await import('https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js');
      await addDoc(collection(db, "notifications"), {
        userId: "global",
        title: title,
        message: message,
        type: type,
        readStatus: [],
        createdAt: new Date().toISOString()
      });
      return true;
    } catch (e) {
      console.error("Error publishing announcement", e);
      return false;
    }
  }

  // Auto-start
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initListeners);
  } else {
    initListeners();
  }

  return {
    publishAnnouncement
  };

})();
