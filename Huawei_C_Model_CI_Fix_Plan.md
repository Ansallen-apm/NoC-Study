Status: OPEN — not yet implemented

huawei_c_model — Add CI Workflow
Background

.github/workflows/ currently only contains noc_c_model_ci.yml（涵蓋另一個獨立模組 noc_c_model）和 auto_merge.yml。目前 huawei_c_model 完全沒有對應的 CI workflow —— 它的 14 個測試檔案（test_config.cpp, test_simulator.cpp, test_single_ring.cpp, test_full_ring.cpp, test_i_tag.cpp, test_e_tag.cpp, test_rbrg_l1.cpp, test_rbrg_l1_backpressure.cpp, test_rbrg_l2.cpp, test_rbrg_l2_credit.cpp, test_swap_deadlock.cpp, test_validation.cpp, test_eject_queue_fuzz.cpp, test_chaos_stress.cpp）目前沒有任何地方會自動建置或執行。

這個缺口的影響比一般的「缺少 CI」更嚴重：auto_merge.yml 讓每個 PR 一開啟就會啟用 gh pr merge --auto，只要滿足 required status checks 跟 branch protection 就會立即合併。因為 huawei_c_model 目前沒有設定任何 required check，只改動這個模組的 PR 完全沒有東西可以等，會在沒有任何自動化驗證的情況下立刻合併。這很可能就是過去一次 regression（EjectQueue::can_reserve() 退回壞掉的舊版本、test_e_tag.cpp/test_i_tag.cpp 同時被換成佔位測試、config.cpp 的欄位驗證被移除——三件事同時發生）能夠進到 main 而沒被機制擋下來的最合理解釋；那次是靠人工複查才被抓到的。

Goal

任何改動 huawei_c_model 的 PR，都必須在可以被視為 mergeable 之前，讓完整測試套件（run_tests）真正被編譯並執行過，做法對齊 noc_c_model_ci.yml 目前已經對 noc_c_model 做的事。

Scope of work
1. 新增 .github/workflows/huawei_c_model_ci.yml

參考現有 noc_c_model_ci.yml 的結構：在 push 和 pull_request 時觸發，用 paths filter（例如 dorny/paths-filter 或等效方式）限定只在 huawei_c_model/** 或這個 workflow 檔案本身有變動時才執行。步驟：checkout、安裝建置依賴（cmake、build-essential；libyaml-cpp-dev/libgtest-dev 是選配，因為 huawei_c_model/CMakeLists.txt 已經有 fallback 會透過 FetchContent 抓 yaml-cpp 和 googletest——兩種方式都可以，但如果走 FetchContent 那 CMake configure 這步需要網路），然後：

cd huawei_c_model
mkdir -p build && cd build
cmake ..
make -j$(nproc)
./run_tests

只要有任何測試失敗，這個 job 就必須是非零退出——./run_tests（GoogleTest binary）本身就會這樣做，不需要額外包裝。

2. 幫 job 取一個穩定、明確的名字，方便之後設成 required status check

名字要清楚穩定（例如 build-and-test，跟現有 noc_c_model_ci.yml 的 job 名稱一致；或用一個明顯不同的名字如 huawei-build-and-test 以便在 branch protection 設定裡區分——兩種都可以，但請在 PR 描述裡明確寫出你選了哪個名字，因為下一步要用到）。

Acceptance criteria
開一個改動 huawei_c_model/ 底下檔案的 PR，會觸發這個新 workflow，且它真的會編譯 run_tests 並執行（可透過檢查 Actions run log 確認有出現 GoogleTest 的輸出，涵蓋目前所有測試套件：Phase1Test 到 Phase6Test、ConfigTest、ValidationTest、EjectQueueFuzzTest、ChaosStressTest、SimulatorTest 等）。
故意在一個暫時性 commit（不要真的提交進 PR——可在本機或一個丟棄用的分支上驗證）裡放入一個會失敗的斷言，確認這會讓 workflow run 失敗，證明它不是空的。
只改動 huawei_c_model/ 以外檔案（且不動這個 workflow 檔案本身）的 PR，不會觸發這個 workflow，符合 paths filter 的設定。
這個 workflow 不會修改或影響現有 noc_c_model_ci.yml 的行為。
Non-goals（不在這個 plan 範圍內，但先標記起來供後續追蹤）
這個 plan 本身無法讓 auto_merge.yml 真的等待這個新 check。 新增 workflow 檔案只是讓這個 check「可以被使用」，但 PR 的 auto-merge 是否會等它，取決於它有沒有在 repo 的 branch protection 設定（Settings → Branches → Branch protection rules）裡被設成 required status check。這是 repo 管理員層級的設定，不是 repo 裡的檔案——沒辦法透過 PR 改動，Jules（透過 PR 運作）沒辦法做這一步。這個 workflow 合併之後，需要 repo owner（不是 Jules）親自到 GitHub branch protection 設定裡，把這個新 job 的名字加進 required status checks 清單，否則這個 plan 原本要補的 auto-merge 缺口，實際上還是沒補到，即使 workflow 檔案已經存在。
不包含幫其他模組（noc_tlm_model、noc_rtl、Python dse_tools）加 CI。
不包含對 noc_c_model_ci.yml 本身的任何改動。
Files likely in scope
新檔案：.github/workflows/huawei_c_model_ci.yml。
.github/workflows/noc_c_model_ci.yml —— 僅供參考，不要修改。
