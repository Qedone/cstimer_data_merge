import json
import os
import sys
import glob


def main():
    print("=== csTimer 备份文件全自动合并工具 ===")

    # 1. 自动搜索当前文件夹下的 txt 文件
    # 排除掉可能已经生成的合并结果文件，防止重复读取
    all_txt_files = [f for f in glob.glob("*.txt") if f != "cstimer_merged_final.txt"]

    # 检查文件数量
    if len(all_txt_files) < 2:
        print(f"错误：当前文件夹下的 txt 文件不足 2 个（目前找到: {all_txt_files}）。")
        print("请确保将两个 csTimer 备份文件都放在这个文件夹里！")
        sys.exit(1)
    elif len(all_txt_files) > 2:
        print(f"警告：当前文件夹下找到了超过 2 个 txt 文件：{all_txt_files}")
        print(
            "为了防止合并错文件，请保证该文件夹下【只有】你需要合并的 2 个 txt 文件，其他的请暂时移出去。"
        )
        sys.exit(1)

    # 按文件名排序，通常 csTimer 导出的文件名带有时间戳，排序后能区分先后
    all_txt_files.sort()
    file_src = all_txt_files[0]
    file_base = all_txt_files[1]

    print(f"自动识别到以下两个文件：")
    print(f" 1. {file_src} (作为成绩补充源)")
    print(f" 2. {file_base} (作为基础主文件)\n")

    # 2. 读取数据
    try:
        with open(file_src, "r", encoding="utf-8") as f:
            data_src = json.load(f)
        with open(file_base, "r", encoding="utf-8") as f:
            data_base = json.load(f)
    except Exception as e:
        print(f"读取文件失败，请检查文件是否为合法的 json/txt: {e}")
        sys.exit(1)

    # 3. 解析 sessionData
    sess_data_src = json.loads(data_src["properties"]["sessionData"])
    sess_data_base = json.loads(data_base["properties"]["sessionData"])

    # 为基础文件建立 {分组名称 : sessionID} 映射字典
    name_to_sid_base = {}
    for sid, sinfo in sess_data_base.items():
        name = str(sinfo.get("name", "")).strip().lower()
        name_to_sid_base[name] = f"session{sid}"

    total_added = 0
    updated_sessions = 0

    print("=== 开始智能匹配分组并合并 ===")

    # 4. 遍历源文件中的所有分组，寻找基础文件中的同名分组
    for sid_src, sinfo_src in sess_data_src.items():
        original_name = str(sinfo_src.get("name", ""))
        match_name = original_name.strip().lower()
        session_key_src = f"session{sid_src}"

        # 如果找到了同名的分组
        if match_name in name_to_sid_base:
            session_key_base = name_to_sid_base[match_name]

            list_src = data_src.get(session_key_src, [])
            list_base = data_base.get(session_key_base, [])

            # 使用 (时间戳, 打乱公式) 作为唯一标识去重
            existing_identifiers = {(solve[3], solve[0][1]) for solve in list_base}

            added_in_current = 0
            for solve in list_src:
                identifier = (solve[3], solve[0][1])
                if identifier not in existing_identifiers:
                    list_base.append(solve)
                    existing_identifiers.add(identifier)
                    added_in_current += 1
                    total_added += 1

            # 如果补充了新成绩，则重新排序并更新
            if added_in_current > 0:
                list_base.sort(key=lambda x: x[3])
                data_base[session_key_base] = list_base
                updated_sessions += 1
                print(
                    f"分组 '{original_name}': 成功补充了 {added_in_current} 条新成绩。"
                )

                # 清除旧统计缓存，使得导入后能够正常计算
                sid_num_base = session_key_base.replace("session", "")
                if "stat" in sess_data_base[sid_num_base]:
                    del sess_data_base[sid_num_base]["stat"]

    # 5. 保存更新后的 sessionData
    data_base["properties"]["sessionData"] = json.dumps(
        sess_data_base, separators=(",", ":")
    )

    # 6. 生成合并好的最终文件
    output_filename = "cstimer_merged_final.txt"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(data_base, f, separators=(",", ":"))

    print("\n=== 合并完成 ===")
    if total_added > 0:
        print(
            f"合并成功！共在 {updated_sessions} 个分组中补充了 {total_added} 条成绩。"
        )
        print(
            f"生成的最新文件名为：{output_filename}，请直接将此文件导入 csTimer 即可。"
        )
    else:
        print("提示：两个文件的同名分组数据已经是一致的，没有发现需要补充的新成绩。")


if __name__ == "__main__":
    main()
