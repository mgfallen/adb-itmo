package handmade_market

import (
	"context"
	"fmt"
	"math"
	"os"
	"testing"
	"time"

	"github.com/jackc/pgx/v5"
)

// testDSN возвращает DSN для интеграционных тестов.
// По умолчанию — postgres из docker-compose.yml. Можно переопределить
// переменной окружения TEST_DATABASE_DSN.
func testDSN() string {
	if v := os.Getenv("TEST_DATABASE_DSN"); v != "" {
		return v
	}
	return "postgres://postgres:postgres@localhost:5435/handmade_market?sslmode=disable"
}

// testSchema создаёт схему и наполняет её тестовыми данными.
var testSchema = []string{
	`DROP TABLE IF EXISTS master_product, "order", product, master, client;`,
	`CREATE TABLE client (
		client_id   BIGINT PRIMARY KEY,
		name        TEXT NOT NULL,
		address     TEXT,
		birthday    DATE,
		email       TEXT
	);`,
	`CREATE TABLE product (
		product_id BIGINT PRIMARY KEY,
		type       TEXT NOT NULL
	);`,
	`CREATE TABLE master (
		master_id BIGINT PRIMARY KEY,
		name      TEXT NOT NULL
	);`,
	`CREATE TABLE master_product (
		master_id BIGINT NOT NULL REFERENCES master (master_id),
		product_id BIGINT NOT NULL REFERENCES product (product_id),
		price      NUMERIC(10, 2) NOT NULL,
		PRIMARY KEY (master_id, product_id)
	);`,
	`CREATE TABLE "order" (
		order_id      BIGINT PRIMARY KEY,
		client_id     BIGINT NOT NULL REFERENCES client (client_id),
		master_id     BIGINT NOT NULL REFERENCES master (master_id),
		product_id    BIGINT NOT NULL REFERENCES product (product_id),
		order_date    DATE NOT NULL,
		delivery_date DATE,
		status        TEXT NOT NULL
	);`,
	`INSERT INTO client (client_id, name, address, birthday, email) VALUES
		(1, 'Иван Иванов', 'Москва', '1995-03-15', 'ivan@example.com'),
		(2, 'Пётр Петров', 'Казань', '1990-01-01', 'petr@example.com');`,
	`INSERT INTO product (product_id, type) VALUES
		(1, 'украшения'),
		(2, 'керамика');`,
	`INSERT INTO master (master_id, name) VALUES
		(1, 'Мария'),
		(2, 'Анна');`,
	`INSERT INTO master_product (master_id, product_id, price) VALUES
		(1, 1, 1000),
		(2, 1, 1200),
		(1, 2, 800),
		(2, 2, 900);`,
	`INSERT INTO "order" (order_id, client_id, master_id, product_id, order_date, delivery_date, status) VALUES
		(1, 1, 1, 1, '2026-10-01', '2026-10-03', 'paid'),
		(2, 1, 1, 2, '2026-10-05', '2026-10-09', 'paid'),
		(3, 1, 2, 1, '2026-10-10', '2026-10-11', 'completed'),
		(4, 2, 1, 1, '2026-09-02', '2026-09-03', 'paid'),
		(5, 2, 2, 2, '2026-09-06', '2026-09-08', 'created'),
		(6, 2, 2, 1, '2026-09-09', '2026-09-09', 'in_progress');`,
}

func TestGetMonthlyReportIntegration(t *testing.T) {
	ctx := context.Background()

	conn, err := pgx.Connect(ctx, testDSN())
	if err != nil {
		t.Skipf("БД недоступна, пропускаю интеграционный тест: %v", err)
	}
	t.Cleanup(func() { conn.Close(context.Background()) })

	for _, stmt := range testSchema {
		if _, err := conn.Exec(ctx, stmt); err != nil {
			t.Fatalf("подготовка данных (%s...): %v", stmt[:30], err)
		}
	}
	t.Cleanup(func() {
		conn.Exec(context.Background(), `DROP TABLE IF EXISTS master_product, "order", product, master, client CASCADE`)
	})

	got, err := NewRepository(conn).GetMonthlyReport(ctx)
	if err != nil {
		t.Fatalf("GetMonthlyReport() error = %v", err)
	}

	cat := "украшения"
	master1 := int64(1)
	master2 := int64(2)
	want := []ReportRow{
		{
			ClientID: 1, ClientName: "Иван Иванов", ClientAddress: "Москва",
			ClientBirthday:  time.Date(1995, 3, 15, 0, 0, 0, 0, time.UTC),
			ClientEmail:     "ivan@example.com",
			TotalPaidAmount: 1800, MonthlyOrdersCount: 3, AvgMonthlyOrderPrice: 1000,
			MedianCompletionDays:   2,
			PopularProductCategory: &cat, PopularMasterID: &master1,
			CountCreated: 0, CountInProgress: 0, CountCompleted: 1, CountUncompleted: 2,
			ReportingPeriod: "2026-10",
		},
		{
			ClientID: 2, ClientName: "Пётр Петров", ClientAddress: "Казань",
			ClientBirthday:  time.Date(1990, 1, 1, 0, 0, 0, 0, time.UTC),
			ClientEmail:     "petr@example.com",
			TotalPaidAmount: 1000, MonthlyOrdersCount: 3, AvgMonthlyOrderPrice: 3100.0 / 3.0,
			MedianCompletionDays:   1,
			PopularProductCategory: &cat, PopularMasterID: &master2,
			CountCreated: 1, CountInProgress: 1, CountCompleted: 0, CountUncompleted: 3,
			ReportingPeriod: "2026-09",
		},
	}

	if len(got) != len(want) {
		t.Fatalf("получено %d строк, ожидалось %d: %#v", len(got), len(want), got)
	}

	for _, exp := range want {
		var actual *ReportRow
		for i := range got {
			if got[i].ClientID == exp.ClientID && got[i].ReportingPeriod == exp.ReportingPeriod {
				actual = &got[i]
				break
			}
		}
		t.Run(fmt.Sprintf("клиент %d за %s", exp.ClientID, exp.ReportingPeriod), func(t *testing.T) {
			if actual == nil {
				t.Fatalf("строка не найдена: %#v", exp)
			}
			assertReportRow(t, *actual, exp)
		})
	}
}

// assertReportRow сравнивает строку отчёта с ожиданием,
// учитывая особенности чисел с плавающей точкой и nullable-полей.
func assertReportRow(t *testing.T, got, want ReportRow) {
	t.Helper()

	if got.ClientID != want.ClientID {
		t.Errorf("ClientID = %d, want %d", got.ClientID, want.ClientID)
	}
	if got.ClientName != want.ClientName {
		t.Errorf("ClientName = %q, want %q", got.ClientName, want.ClientName)
	}
	if got.ClientAddress != want.ClientAddress {
		t.Errorf("ClientAddress = %q, want %q", got.ClientAddress, want.ClientAddress)
	}
	if !got.ClientBirthday.Equal(want.ClientBirthday) {
		t.Errorf("ClientBirthday = %v, want %v", got.ClientBirthday, want.ClientBirthday)
	}
	if got.ClientEmail != want.ClientEmail {
		t.Errorf("ClientEmail = %q, want %q", got.ClientEmail, want.ClientEmail)
	}
	if !approxEqual(got.TotalPaidAmount, want.TotalPaidAmount) {
		t.Errorf("TotalPaidAmount = %v, want %v", got.TotalPaidAmount, want.TotalPaidAmount)
	}
	if got.MonthlyOrdersCount != want.MonthlyOrdersCount {
		t.Errorf("MonthlyOrdersCount = %d, want %d", got.MonthlyOrdersCount, want.MonthlyOrdersCount)
	}
	if !approxEqual(got.AvgMonthlyOrderPrice, want.AvgMonthlyOrderPrice) {
		t.Errorf("AvgMonthlyOrderPrice = %v, want %v", got.AvgMonthlyOrderPrice, want.AvgMonthlyOrderPrice)
	}
	if !approxEqual(got.MedianCompletionDays, want.MedianCompletionDays) {
		t.Errorf("MedianCompletionDays = %v, want %v", got.MedianCompletionDays, want.MedianCompletionDays)
	}
	if !ptrStringEqual(got.PopularProductCategory, want.PopularProductCategory) {
		t.Errorf("PopularProductCategory = %v, want %v", deref(got.PopularProductCategory), deref(want.PopularProductCategory))
	}
	if !ptrIntEqual(got.PopularMasterID, want.PopularMasterID) {
		t.Errorf("PopularMasterID = %v, want %v", deref(got.PopularMasterID), deref(want.PopularMasterID))
	}
	if got.CountCreated != want.CountCreated {
		t.Errorf("CountCreated = %d, want %d", got.CountCreated, want.CountCreated)
	}
	if got.CountInProgress != want.CountInProgress {
		t.Errorf("CountInProgress = %d, want %d", got.CountInProgress, want.CountInProgress)
	}
	if got.CountCompleted != want.CountCompleted {
		t.Errorf("CountCompleted = %d, want %d", got.CountCompleted, want.CountCompleted)
	}
	if got.CountUncompleted != want.CountUncompleted {
		t.Errorf("CountUncompleted = %d, want %d", got.CountUncompleted, want.CountUncompleted)
	}
	if got.ReportingPeriod != want.ReportingPeriod {
		t.Errorf("ReportingPeriod = %q, want %q", got.ReportingPeriod, want.ReportingPeriod)
	}
}

func approxEqual(a, b float64) bool {
	return math.Abs(a-b) < 1e-6
}

func ptrStringEqual(a, b *string) bool {
	if a == nil || b == nil {
		return a == b
	}
	return *a == *b
}

func ptrIntEqual(a, b *int64) bool {
	if a == nil || b == nil {
		return a == b
	}
	return *a == *b
}

func deref[T any](p *T) T {
	var zero T
	if p == nil {
		return zero
	}
	return *p
}
