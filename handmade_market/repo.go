package handmade_market

import (
	"context"

	"github.com/jackc/pgx/v5"
)

type DBTX interface {
	Query(ctx context.Context, sql string, args ...any) (pgx.Rows, error)
}

type Repository struct {
	db DBTX
}

func NewRepository(db DBTX) *Repository {
	return &Repository{db: db}
}

const monthlyReportQuery = `
WITH order_details AS (
   SELECT
      o.order_id,
      o.client_id,
      o.master_id,
      o.product_id,
      p.type AS product_type,
      mp.price,
      o.order_date,
      o.delivery_date,
      o.status,
      TO_CHAR(o.order_date, 'YYYY-MM') AS reporting_period
   FROM "order" o
   JOIN client c ON o.client_id = c.client_id
   JOIN product p ON o.product_id = p.product_id
   LEFT JOIN master_product mp ON o.master_id = mp.master_id AND o.product_id = mp.product_id
),
client_monthly AS (
   SELECT
      od.client_id,
      od.reporting_period,
      (
         SELECT SUM(mp_all.price)
         FROM "order" o_all
         JOIN master_product mp_all
           ON o_all.master_id = mp_all.master_id AND o_all.product_id = mp_all.product_id
         WHERE o_all.client_id = od.client_id AND o_all.status = 'paid'
      ) AS total_paid_amount,
      COUNT(od.order_id) AS monthly_orders_count,
      AVG(od.price) AS avg_monthly_order_price,
      SUM(CASE WHEN od.status = 'created' THEN 1 ELSE 0 END) AS count_created,
      SUM(CASE WHEN od.status = 'in_progress' THEN 1 ELSE 0 END) AS count_in_progress,
      SUM(CASE WHEN od.status = 'completed' THEN 1 ELSE 0 END) AS count_completed,
      SUM(CASE WHEN od.status != 'completed' THEN 1 ELSE 0 END) AS count_uncompleted,
      PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY (od.delivery_date - od.order_date)) AS median_completion_days
   FROM order_details od
   GROUP BY od.client_id, od.reporting_period
),
popular_category AS (
   SELECT client_id, reporting_period, product_type,
         ROW_NUMBER() OVER (PARTITION BY client_id, reporting_period ORDER BY COUNT(*) DESC, product_type) as rn
   FROM order_details
   GROUP BY client_id, reporting_period, product_type
),
popular_master AS (
   SELECT client_id, reporting_period, master_id,
         ROW_NUMBER() OVER (PARTITION BY client_id, reporting_period ORDER BY COUNT(*) DESC, master_id) as rn
   FROM order_details
   GROUP BY client_id, reporting_period, master_id
)
SELECT
   ROW_NUMBER() OVER (ORDER BY cm.reporting_period, c.client_id) AS record_id,
   c.client_id,
   c.name AS client_name,
   c.address AS client_address,
   c.birthday AS client_birthday,
   c.email AS client_email,
   cm.total_paid_amount,
   cm.monthly_orders_count,
   cm.avg_monthly_order_price,
   cm.median_completion_days,
   pc.product_type AS popular_product_category,
   pm.master_id AS popular_master_id,
   cm.count_created,
   cm.count_in_progress,
   cm.count_completed,
   cm.count_uncompleted,
   cm.reporting_period
FROM client c
JOIN client_monthly cm ON c.client_id = cm.client_id
LEFT JOIN popular_category pc
  ON c.client_id = pc.client_id AND cm.reporting_period = pc.reporting_period AND pc.rn = 1
LEFT JOIN popular_master pm
  ON c.client_id = pm.client_id AND cm.reporting_period = pm.reporting_period AND pm.rn = 1;
`

func (r *Repository) GetMonthlyReport(ctx context.Context) ([]ReportRow, error) {
	rows, err := r.db.Query(ctx, monthlyReportQuery)
	if err != nil {
		return nil, err
	}

	results, err := pgx.CollectRows(rows, pgx.RowToStructByName[ReportRow])
	if err != nil {
		return nil, err
	}

	return results, nil
}
