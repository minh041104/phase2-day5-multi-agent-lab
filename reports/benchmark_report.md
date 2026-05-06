# Báo Cáo Benchmark

| Lần chạy | Độ trễ (s) | Chi phí (USD) | Chất lượng | Độ phủ citation | Tỉ lệ lỗi | Số trace event | Ghi chú |
|---|---:|---:|---:|---:|---:|---:|---|
| baseline-q1 | 11.55 | 0.0045 | 6.3 | 63% | 0% | 1 | ok |
| multi-agent-q1 | 23.60 | 0.0137 | 9.0 | 50% | 0% | 7 | ok |
| baseline-q2 | 6.52 | 0.0036 | 6.6 | 82% | 0% | 1 | ok |
| multi-agent-q2 | 24.80 | 0.0150 | 9.4 | 69% | 0% | 7 | ok |
| baseline-q3 | 6.63 | 0.0042 | 6.8 | 88% | 0% | 1 | ok |
| multi-agent-q3 | 21.43 | 0.0155 | 9.7 | 86% | 0% | 7 | ok |

## Ghi Chú

- Điểm chất lượng là điểm heuristic ban đầu; rubric peer review vẫn là đánh giá cuối cùng của con người.
- Độ phủ citation ước lượng tỉ lệ các câu quan trọng trong câu trả lời cuối có citation dạng `[1]`, `[2]`.
- Tỉ lệ lỗi là 100% nếu một lần chạy thất bại và 0% nếu lần chạy thành công.

## Tóm Tắt Kết Quả

Kết quả benchmark cho thấy sự đánh đổi rõ ràng giữa baseline single-agent và workflow multi-agent.

Workflow multi-agent đạt điểm chất lượng cao hơn trên cả ba query benchmark:

- Query 1: multi-agent 9.0 so với baseline 6.3.
- Query 2: multi-agent 9.4 so với baseline 6.6.
- Query 3: multi-agent 9.7 so với baseline 6.8.

Baseline nhanh hơn và rẻ hơn. Độ trễ của baseline nằm trong khoảng 6.52s đến 11.55s, trong khi độ trễ của multi-agent nằm trong khoảng 21.43s đến 24.80s. Chi phí của baseline nằm trong khoảng 0.0036 USD đến 0.0045 USD, trong khi chi phí của multi-agent nằm trong khoảng 0.0137 USD đến 0.0155 USD.

Cả hai cách đều hoàn thành tất cả lần chạy benchmark với tỉ lệ lỗi 0%. Workflow multi-agent tạo 7 trace event cho mỗi lần chạy, trong khi baseline chỉ tạo 1 trace event. Vì vậy multi-agent dễ quan sát, giải thích và debug hơn.

## Nhận Xét

Workflow multi-agent phù hợp hơn khi cần chất lượng đầu ra cao, trace rõ ràng, và phân tách trách nhiệm giữa các bước. Researcher, Analyst và Writer đều tạo kết quả trung gian, nên dễ xác định câu trả lời yếu đến từ bước nào.

Baseline single-agent phù hợp hơn khi task đơn giản, cần phản hồi nhanh, hoặc cần tối ưu chi phí. Baseline dùng ít model call hơn nên chạy nhanh hơn và tốn ít chi phí hơn.

## Lỗi Có Thể Gặp Và Cách Khắc Phục

Lỗi có thể gặp: multi-agent cải thiện chất lượng nhưng làm tăng độ trễ và chi phí vì mỗi query cần nhiều lần gọi mô hình. Độ phủ citation cũng vẫn có thể yếu ở một số trường hợp; ví dụ multi-agent-q1 chỉ đạt 50%.

Cách fix: giữ guardrail `max_iterations`, dùng routing deterministic trong Supervisor, yêu cầu Writer cite các factual claims bằng citation dạng `[1]`, `[2]`, và dùng Analyst để đánh dấu evidence yếu trước khi Writer tạo câu trả lời cuối. Với query đơn giản, nên dùng baseline single-agent để giảm chi phí và độ trễ.

## Exit Ticket

1. Case nào nên dùng multi-agent?  
   Nên dùng multi-agent khi task có nhiều bước rõ ràng như tìm nguồn, phân tích, viết và kiểm tra citation. Multi-agent phù hợp vì có trace tốt hơn, vai trò rõ hơn, và benchmark cho thấy chất lượng cao hơn baseline.

2. Case nào không nên dùng multi-agent?  
   Không nên dùng multi-agent cho task đơn giản, task cần phản hồi nhanh, hoặc task cần tối ưu chi phí. Benchmark cho thấy multi-agent chậm hơn và tốn chi phí hơn baseline single-agent.
