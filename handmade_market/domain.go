package handmade_market

import "time"

// Client — заказчик (таблица client).
type Client struct {
	ClientID int64
	Name     string
	Address  *string
	Birthday *time.Time
	Email    *string
}

// Master — мастер ручной работы (таблица master).
type Master struct {
	MasterID int64
	Name     string
}

// Product — товар / категория товара (таблица product).
type Product struct {
	ProductID int64
	Type      string
}

// MasterProduct — цена товара у конкретного мастера (таблица master_product).
type MasterProduct struct {
	MasterID  int64
	ProductID int64
	Price     float64
}

// Допустимые статусы заказа (таблица "order").
const (
	OrderStatusCreated    = "created"     // создан
	OrderStatusInProgress = "in_progress" // в процессе изготовления
	OrderStatusCompleted  = "completed"   // завершён
	OrderStatusPaid       = "paid"        // оплачен
)

// Order — заказ (таблица "order").
type Order struct {
	OrderID      int64
	ClientID     int64
	MasterID     int64
	ProductID    int64
	OrderDate    time.Time
	DeliveryDate *time.Time
	Status       string
}
