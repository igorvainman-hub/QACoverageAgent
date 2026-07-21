# System Overview

## Ecommerce/Order

Пользователь создаёт заказ через корзину, заказ проходит статусы Draft → Pending → Paid/Cancelled/Shipped. Отмена доступна только в Draft/Pending.

## Payment-Feature

The Payment-Feature handles processing payments for orders, including initiating, completing, and refunding transactions. The new test cases (QA-001 to QA-005) focus on verifying order status transitions such as cancellations from Draft or Pending states, restrictions on cancellation for Paid, Cancelled, or Shipped orders, and ensuring notifications are sent upon payment completion with Stripe integration. Additionally, concurrency issues during transaction cancellations and retries across different sessions or devices are examined. This feature is integrated with the order management system to update statuses and communicate changes, and it interacts with notification systems to alert users of status changes.
