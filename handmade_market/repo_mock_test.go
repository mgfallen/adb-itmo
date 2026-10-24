package handmade_market

import (
	"context"
	"testing"
	"time"

	"github.com/pashagolub/pgxmock/v5"
)

// TestGetMonthlyReportMock проверяет сборку строк витрины без БД:
// запрос мокается, подставляются две строки ответа. Скалярные поля
// первой строки должны заполниться, NULL-поля — остаться nil.
func TestGetMonthlyReportMock(t *testing.T) {
	mock, err := pgxmock.NewConn()
	if err != nil {
		t.Fatalf("pgxmock.NewConn(): %v", err)
	}

	address := "Москва"
	birthday := time.Date(1995, 3, 15, 0, 0, 0, 0, time.UTC)
	rows := pgxmock.NewRows([]string{
		"record_id", "client_id", "client_name", "client_address",
		"client_birthday", "client_email", "total_paid_amount",
		"monthly_orders_count", "avg_monthly_order_price",
		"median_completion_days", "popular_product_category",
		"popular_master_id", "count_created", "count_in_progress",
		"count_completed", "count_uncompleted", "reporting_period",
	}).AddRow(
		1, 1, "Иван Иванов", address, birthday, "ivan@example.com",
		1800.0, 3, 1000.0, 2.0, nil, nil,
		0, 0, 1, 2, "2026-10",
	).AddRow(
		2, 2, "Пётр Петров", "Казань", time.Time{}, "",
		0.0, 0, 0.0, 0.0, nil, nil,
		0, 0, 0, 0, "2026-09",
	)
	mock.ExpectQuery(`SELECT`).WillReturnRows(rows)

	got, err := NewRepository(mock).GetMonthlyReport(context.Background())
	if err != nil {
		t.Fatalf("GetMonthlyReport() error = %v", err)
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatalf("ожидания мока не выполнены: %v", err)
	}

	if len(got) != 2 {
		t.Fatalf("получено %d строк, ожидалось 2", len(got))
	}

	first := got[0]
	if first.RecordID != 1 || first.ClientID != 1 || first.ClientName != "Иван Иванов" {
		t.Errorf("первая строка собрана неверно: %#v", first)
	}
	if first.ClientAddress != "Москва" || first.TotalPaidAmount != 1800 || first.MedianCompletionDays != 2 {
		t.Errorf("скалярные поля собраны неверно: %#v", first)
	}
	if first.PopularProductCategory != nil || first.PopularMasterID != nil {
		t.Errorf("NULL-поля должны остаться nil: %#v", first)
	}

	// Вторая строка: популярные категория и мастер NULL — должны остаться nil.
	second := got[1]
	if second.ClientID != 2 || second.ReportingPeriod != "2026-09" {
		t.Errorf("вторая строка собрана неверно: %#v", second)
	}
	if second.TotalPaidAmount != 0 || second.PopularProductCategory != nil || second.PopularMasterID != nil {
		t.Errorf("NULL-показатели витрины должны быть пустыми: %#v", second)
	}
}
